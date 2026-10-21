#!/usr/bin/env python3
"""studio.py - the figure studio: one *.kit.json drawn, audited and photographed in seconds, without a module compile.

  studio.py <figure.kit.json> [--parts kit_parts.js] [--panel two-col|dark|wide-left|task|WxH]
            [--sizes 1280x800,1024x768] [--step final|N|all] [--out <folder>] [--json]

WHY (IGF M01-M04, 2026-10-16): the modules took 3, ~10, ~12 and 17 compile runs, nearly all for drawings - a label
overflowing, a part invisible on the dark panel, empty space, a 12 px label - each found only after a full build and its
drawing check. The studio gives the same answers for one figure at a time:

  1  the figure as the deck shows it. A spec inside a course (<course>/working_claude/figures/MNN/sNN.kit.json) is drawn
     on its REAL slide - the script's words, the build sheet's layout, the module's style files - built by the
     compiler's own slide_html. A spec anywhere else is drawn in a slide frame of the --panel kind. --panel task on a spec a
     course's task question stands on (2.52.1) draws that question's REAL task page (task_pages.page_html) - the frame the
     build's drawing check measures - and photographs it; outside a course it is a generic 640 px task frame.
  2  at 1280 x 800 and 1024 x 768, every step: audit_drawing.js (inside, cut off, text zone, empty, contrast, small
     text) and the kit's own layout report (scale, the 12.5 px floor, labels moved, labels with no clear place)
  3  a screenshot per size, of the --step (default: the last), into --out (default: next to the spec, _studio/).
     --step all draws the whole sequence - the rest state and the end of every step - as ONE contact sheet in a single
     browser run (the panels as wide as the real slide's), instead of one run per step

Exit 0 clean, 1 findings, 2 could not run (no Chrome or Edge: set CF_BROWSER).
"""
from __future__ import annotations

import argparse
import glob
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_SLIDE_LOCK = threading.Lock()
# 2.62.1 - the slide as compiled, per figure version, for this process: each size and mode built the whole deck again
# (0.3-0.5 s a compile, behind _SLIDE_LOCK - up to 108 queued in one COLUMN fix round of figure_fit.py)
_SLIDE_MEMO = {}

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
SKILLS = os.path.dirname(os.path.dirname(KIT))
TOKENS = os.path.join(SKILLS, "course-module-ui", "templates")
ASSETS = os.path.join(SKILLS, "course-module-ux", "assets")
AUDIT = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "audit_drawing.js")
COMPILE = os.path.join(SKILLS, "course-factory", "compile", "scripts")
FACTORY_SCRIPTS = os.path.join(SKILLS, "course-factory", "scripts")
sys.path.insert(0, FACTORY_SCRIPTS)
OUT_ID = "__studio_out"
INSET_OVER = None       # (x, y, w) in the drawing's units: draw a stand-in photo over the figure (--inset-over), as the compiler's "over" does
PANELS = ("two-col", "dark", "wide-left", "task")


def find_browser():
    from measure_slides import find_browser as fb
    return fb()


def uri(p):
    return Path(os.path.abspath(p)).as_uri()


# ------------------------------------------------------------------ where the figure lives
def course_context(spec_path):
    """(course, module number, screen id, build entry) when the spec sits in a course's figures folder, else None"""
    p = Path(os.path.abspath(spec_path))
    if len(p.parts) < 4 or p.parent.parent.name.lower() != "figures" or not re.fullmatch(r"M\d\d", p.parent.name, re.I):
        return None
    work = p.parent.parent.parent
    course = work.parent
    mod = int(p.parent.name[1:])
    build = work / "script" / ("M%02d.build.json" % mod)
    script = work / "script" / ("M%02d.json" % mod)
    if not (build.is_file() and script.is_file()):
        return None
    b = json.load(io.open(build, encoding="utf-8"))
    for sid, entry in (b.get("screens") or {}).items():
        if (entry.get("figure") or "").strip() == p.name:
            return {"course": str(course), "work": str(work), "module": mod, "screen": sid, "build": b,
                    "script": str(script), "entry": entry}
    return None


def task_context(spec_path):
    """(course, module, question id, build entry) when the spec sits in a course's figures folder and a TASK question is
    answered on it or shows it - the first such question in the build sheet - else None (2.52.1)"""
    p = Path(os.path.abspath(spec_path))
    if len(p.parts) < 4 or p.parent.parent.name.lower() != "figures" or not re.fullmatch(r"M\d\d", p.parent.name, re.I):
        return None
    work = p.parent.parent.parent
    mod = int(p.parent.name[1:])
    build, script = work / "script" / ("M%02d.build.json" % mod), work / "script" / ("M%02d.json" % mod)
    if not (build.is_file() and script.is_file()):
        return None
    import content_script as cs
    b, sc = json.load(io.open(build, encoding="utf-8")), json.load(io.open(script, encoding="utf-8"))
    tasks = [s["id"] for s in sc.get("screens") or [] if s.get("kind") in cs.TASKS]
    for sid in tasks:
        entry = (b.get("screens") or {}).get(sid) or {}
        if (entry.get("figure") or "").strip() == p.name:
            return {"course": str(work.parent), "work": str(work), "module": mod, "screen": sid, "build": b,
                    "script": str(script), "entry": entry, "page": True}
    return None


# a task page with ONE question shown, its shared drawing moved into it (as gb_answer.js does), then measured by the
# drawing audit exactly as the build's drawing check measures the page (drawing_check.py TASK) - and its frame's size
TASK_PROBE = r"""<script src="%(audit)s"></script><script>
setTimeout(function(){var out={states:[]};try{
 var s=document.querySelector('.scr[data-script="%(qid)s"]');
 [].forEach.call(document.querySelectorAll('.scr'),function(x){x.classList.remove('on');});s.classList.add('on');
 [].forEach.call(s.querySelectorAll('.ga[data-fig]'),function(h){var v=document.querySelector('svg.taskfig[data-fig="'+
   h.getAttribute('data-fig')+'"]');if(v&&v.parentNode!==h){h.insertBefore(v,h.firstChild);}});
 if(window.KIT&&KIT.layoutAll){KIT.layoutAll(true);}
 var g=s.querySelector('.ga'),sv=g&&g.querySelector('svg'),gr=g?g.getBoundingClientRect():{width:0,height:0},
     vr=sv?sv.getBoundingClientRect():{width:0,height:0};
 var st={step:'page',svg:[Math.round(vr.width),Math.round(vr.height)],panel:[Math.round(gr.width),Math.round(gr.height)],findings:[]};
 if(!%(shot)s){var r=AuditDrawing.page();if(r.ABORTED){st.aborted=r.ABORTED;}
  (r.findings||[]).forEach(function(f){st.findings.push({check:f.check,where:f.where,part:f.part,other:f.other||'',detail:f.detail||''});});}
 out.states.push(st);if(sv&&sv.__kit&&sv.__kit.report){out.report=sv.__kit.report;}}catch(e){out.error=String(e);}
 var p=document.createElement('pre');p.id='%(out)s';p.textContent=JSON.stringify(out);if(!%(shot)s){document.body.appendChild(p);}
},400);</script>"""


def task_page_run(spec_path, spec, ctx, sizes, out, shots):
    """2.52.1 - a spec a task question stands on, drawn on the REAL task page as the compiler builds it (task_pages.page_html:
    its width and layout, its step, the words taken off, the label bands) - the frame the build's drawing check measures. The
    M01 rebuild of 2026-10-20: the studio's 640 px task panel said clean, the build's 969 x 500 frame failed it twice (EMPTY)."""
    sys.path.insert(0, COMPILE)
    import compile_module as cm
    import content_script as cs
    import task_pages
    import drawing_check
    script = cs.load(ctx["script"])
    hit = next(((sl, code, qs) for sl, code, qs in task_pages.sets(script) if any(q["id"] == ctx["screen"] for q in qs)), None)
    mdir = os.path.join(ctx["course"], "modules", "module%02d" % ctx["module"])
    if not hit or not os.path.isdir(os.path.join(mdir, "assets")):
        return None, "the task page of %s cannot be built (no set or no module folder)" % ctx["screen"]
    slide, code, qs = hit
    figdir = os.path.join(ctx["work"], "figures", "M%02d" % ctx["module"])
    with _SLIDE_LOCK:
        task_pages.TRY.clear()
        task_pages.TRY[os.path.basename(spec_path)] = spec      # the spec given (a candidate), never a stale fit
        try:
            page = task_pages.page_html(script, slide, code, qs, ctx["build"], mdir, figdir, "STUDIO", True, False, [])
        finally:
            task_pages.TRY.clear()
    where = os.path.dirname(task_pages.page_path(mdir, slide, code, script))
    os.makedirs(where, exist_ok=True)
    exe = find_browser()
    res, files = {}, []
    stem = os.path.basename(spec_path).replace(".kit.json", "")
    out = out or os.path.join(os.path.dirname(os.path.abspath(spec_path)), "_studio")
    tmp = tempfile.mkdtemp(prefix="kit_studio_task_")
    try:
        base = '<base href="%s/">' % Path(where).as_uri()
        for size in sizes:
            key = "%dx%d" % size
            r = res.setdefault(key, {"states": [], "report": {}})
            for mode in ("probe", "shot") if shots else ("probe",):
                f = os.path.join(where, "__studio_%s_%s_%s.html" % (ctx["screen"], key, mode))
                files.append(f)
                doc = re.sub(r"<head>", "<head>" + base, page, count=1, flags=re.I)
                probe = TASK_PROBE % {"audit": uri(AUDIT), "qid": ctx["screen"], "out": OUT_ID, "shot": "true" if mode == "shot" else "false"}
                i = doc.lower().rfind("</body>")
                io.open(f, "w", encoding="utf-8").write(doc[:i] + probe + doc[i:] if i >= 0 else doc + probe)
                prof = tempfile.mkdtemp(prefix="p_", dir=tmp)
                if mode == "shot":
                    os.makedirs(out, exist_ok=True)
                    png = os.path.join(out, "%s_%s_task_%s.png" % (stem, ctx["screen"], key))
                    ok, _ = chrome(exe, uri(f), size, prof, png).wait(60)
                    r["shot"] = png if os.path.isfile(png) else None
                    continue
                ok, so = chrome(exe, uri(f), drawing_check.window_for(exe, size), prof).wait(90)
                m = re.search(r'<pre id="%s">(.*?)</pre>' % OUT_ID, so or "", re.S)
                if not m:
                    r["error"] = "the task page did not finish in the hidden browser"
                    continue
                got = json.loads(html.unescape(m.group(1)))
                if got.get("error"):
                    r["error"] = got["error"]
                r["states"] = got.get("states") or []
                r["report"] = got.get("report") or {}
    finally:
        for f in files:
            if os.path.isfile(f):
                os.remove(f)
        shutil.rmtree(tmp, ignore_errors=True)
    return {"sizes": res, "context": {"module": ctx["module"], "screen": ctx["screen"], "page": True}, "notes": []}, None


def real_slide(ctx):
    """the slide as the compiler builds it, and the module folder its assets come from - or (None, why)"""
    sys.path.insert(0, COMPILE)
    try:
        import compile_module as cm
        import content_script as cs
    except Exception as err:                       # noqa: BLE001 - the studio still works without the course
        return None, None, "the compiler could not be loaded (%s)" % err
    script = cs.load(ctx["script"])
    screens = [s for s in script["screens"] if s["kind"] in cs.INSTRUCTOR]
    s = next((x for x in screens if x["id"] == ctx["screen"]), None)
    if not s:
        return None, None, "screen %s is not in the script" % ctx["screen"]
    mdir = os.path.join(ctx["course"], "modules", "module%02d" % ctx["module"])
    if not os.path.isdir(os.path.join(mdir, "assets")):
        return None, None, "the module folder %s has no assets" % mdir
    figdir = os.path.join(ctx["work"], "figures", "M%02d" % ctx["module"])
    probs = []
    name = os.path.basename(ctx["entry"].get("figure") or "")

    def stamp(p):
        try:
            return os.path.getmtime(p)
        except OSError:
            return None
    memo = json.dumps([ctx["script"], ctx["screen"], ctx["module"], ctx["entry"], ctx.get("spec_override"), ctx["build"],
                       stamp(ctx["script"])] + [stamp(os.path.join(ctx["work"], "_build", "M%02d_%s.json" % (ctx["module"], k)))
                                                 for k in ("layout_avoid", "layouts")], sort_keys=True, default=str)
    with _SLIDE_LOCK:                          # figure_fit.py runs several studios at once, in threads
        if memo in _SLIDE_MEMO:
            return dict(_SLIDE_MEMO[memo]), mdir, None
        cm.OVERRIDE.clear()
        if ctx.get("spec_override") is not None:     # draw the spec given (a candidate fix), else the file - never a stale fit
            cm.OVERRIDE[name] = ctx["spec_override"]
        try:
            # 2.50.1 - the slide cut out of the whole deck as the compiler builds it, so it carries what the build puts beside
            # the figure: the L57 photo row under it, an inset (IGF M01 benchmark: the studio drew s05 in a 369 x 361 panel,
            # the build in 369 x 239 under its photo row - a figure clean in the studio failed the build twice)
            build = dict(ctx["build"], screens=dict(ctx["build"].get("screens") or {}, **{s["id"]: ctx["entry"]}))
            # 2.62.1 - with the layouts build_module.py measured out, as the compile builds the deck: without them a figure
            # was fitted to a column the deck no longer gave it after a layout retry
            mid_ = "M%02d" % ctx["module"]
            deck, _, _ = cm.compile_deck(script, build, mdir, figdir, "STUDIO", True, cm.load_layout_avoid(ctx["work"], mid_),
                                         cm.load_layouts(ctx["work"], mid_))
            m = re.search(r'<section [^>]*\bid="%s"[^>]*>.*?</section>' % re.escape(s["id"]), deck, re.S)
            page = m.group(0) if m else cm.slide_html(script, s, 1, len(screens), ctx["entry"], mdir, figdir, "STUDIO", probs)
        finally:
            cm.OVERRIDE.clear()
    styles = list(cm.STYLES) + ["gb_zoom.css", "kit.css"]
    extra = ["../" + x for x in ctx["build"].get("styles", [])]
    chrome = ('<div id="landing"><div class="landing-card"><button id="startBtn" type="button"><span class="btn-label">Start'
              '</span></button></div></div>' + cm.chrome_block())
    real = {"slide": page, "mdir": mdir, "styles": styles, "extra": extra, "probs": probs, "chrome": chrome}
    with _SLIDE_LOCK:
        _SLIDE_MEMO[memo] = real
    return dict(real), mdir, None


def generic_slide(spec, panel):
    """a slide frame of the panel kind with the spec in it - the compiler's markup for a kit figure"""
    data = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    svg = '<svg data-kit="#kit-studio"></svg>'
    if INSET_OVER and panel != "task":      # a photo laid over a blank part of the drawing, as the compiler's "over" does (F4)
        x, y, w = INSET_OVER
        sw, sh = spec["size"]
        photo = ('<figure class="inset over" style="left:%.2f%%;top:%.2f%%;width:%.2f%%"><img alt="photo" src="data:image/svg+xml,'
                 '%%3Csvg xmlns=%%27http://www.w3.org/2000/svg%%27 viewBox=%%270 0 16 9%%27%%3E%%3Crect width=%%2716%%27 height=%%279%%27 '
                 'fill=%%27%%23556%%27/%%3E%%3C/svg%%3E"><figcaption>a photograph</figcaption></figure>'
                 % (100 * x / sw, 100 * y / sh, 100 * w / sw))
        svg = '<div class="kit-holder">%s%s</div>' % (svg, photo)
    fig = ('<div class="fill fig kit-fig" data-kit-scope><div class="kit-screen">%s</div>'
           '<script type="application/json" id="kit-studio">%s</script>%s</div>'
           % (svg, data,'<div class="mediabar"><button class="fbtn" type="button" data-act="prev">Previous step</button>'
                    '<span class="dots"></span><button class="fbtn primary" type="button" data-act="next">Next step</button>'
                    '<button class="fbtn" type="button" data-act="replay">Replay</button></div>' if spec.get("steps") else ""))
    if panel == "task":
        return ('<div class="studio-task"><div class="ga" style="--ar:%.3f"><svg class="taskfig" data-kit="#kit-studio" '
                'data-kit-step="final"></svg><script type="application/json" id="kit-studio">%s</script></div></div>'
                % (spec["size"][0] / float(spec["size"][1]), data))
    m = re.fullmatch(r"(\d+)x(\d+)", panel or "")
    if m:
        return ('<div class="studio-box" style="width:%spx;height:%spx">%s</div>' % (m.group(1), m.group(2), fig))
    words = "".join('<li data-i="%d">Line %d of the slide, beside the figure, at reading size.</li>' % (i, i) for i in range(2, 6))
    cls = {"two-col": "two-col fig-wide", "wide-left": "wide-left", "dark": "two-col fig-wide"}.get(panel, "two-col fig-wide")
    dark = " dark" if panel == "dark" else ""
    return ('<section class="slide%s" id="studio"><div class="slide-kind"><b>Studio</b></div><h2>The figure in its slide</h2>'
            '<div class="slide-body %s"><div class="copy"><p class="statement" data-i="1">The statement of the slide.</p>'
            '<ul class="support">%s</ul></div>%s</div></section>' % (dark, cls, words, fig))


PROBE = r"""
<script src="%(audit)s"></script>
<script>
(function () {
  var SHOT = %(shot)s;
  function out(r) { r.virt = Math.round(performance.now()); var p = document.createElement('pre'); p.id = '%(out)s'; p.textContent = JSON.stringify(r); document.body.appendChild(p); }
  function frames(n, cb) { setTimeout(cb, 40 * n); }      // a hidden browser's virtual clock runs timers, not frames
  function run() {
    var sb = document.getElementById('startBtn');
    if (sb && getComputedStyle(sb).display !== 'none') sb.click();
    setTimeout(function () {
      var svg = document.querySelector('svg[data-kit]'), f = svg && svg.__kit;
      if (!f) { out({ error: 'the figure was not drawn: ' + ((document.querySelector('.kit-error') || {}).textContent || 'no kit.js?') }); return; }
      var res = { viewport: [innerWidth, innerHeight], steps: f.steps(), states: [] };
      if (SHOT !== null) {
        var n = SHOT === 'final' ? f.steps() : Math.min(+SHOT, f.steps());
        f.go(n, true);
        /* the picture is taken when the hidden browser's clock runs out; a flow that never ends keeps it from running
           out, so every animation is held where it is */
        frames(3, function () {
          f.layout();
          if (document.getAnimations) document.getAnimations().forEach(function (a) {   // a slide's fade-in ends, a flow stops
            try { var t = a.effect && a.effect.getTiming ? a.effect.getTiming() : {}; if (t.iterations === Infinity) a.pause(); else a.finish(); } catch (e) {}
          });
          f.stop();
          document.documentElement.setAttribute('data-studio-done', '1');
        });
        return;
      }
      var k = 0, boxes = {};
      /* 2.50.0 - every part's box in the drawing's own units (its labels inside it, as laid out), joined over the steps:
         what figure_fit.py needs to crop a drawing to what it shows, or to re-flow it into another column */
      function partBoxes() {
        var specParts = f.spec.parts || [];
        f.list.forEach(function (part) {
          if (!part.g || part.id && part.id.indexOf('.') > 0 || getComputedStyle(part.g).display === 'none') return;
          var i = specParts.indexOf(part.p);             // keyed by the part's place in the spec (a repeater: by its id)
          if (i < 0 && part.id) specParts.forEach(function (q, j) { if (q.id === part.id) i = j; });
          if (i < 0) return;
          var b; try { b = part.g.getBBox(); } catch (e) { return; }
          if (!b || (!b.width && !b.height)) return;
          var p = part.p || {}, x0 = (p.x || 0) + b.x, y0 = (p.y || 0) + b.y, key = String(i), o = boxes[key];
          boxes[key] = o ? [Math.min(o[0], x0), Math.min(o[1], y0), Math.max(o[2], x0 + b.width), Math.max(o[3], y0 + b.height), p.id || '', p.type]
                         : [x0, y0, x0 + b.width, y0 + b.height, p.id || '', p.type];
        });
      }
      (function next() {
        if (k > f.steps()) { res.report = f.layout(true); res.parts = boxes; out(res); return; }
        f.go(k, true);
        frames(2, function () {
          partBoxes();
          var a = AuditDrawing.figure(svg, 'step ' + k);
          var sb2 = svg.getBoundingClientRect(), host = svg.closest('.kit-screen') || svg.parentNode, hb = host.getBoundingClientRect();
          res.states.push({ step: k, findings: (a.findings || []).map(function (x) { return { check: x.check, part: x.part, other: x.other || '', detail: x.detail || '' }; }),
                            aborted: a.ABORTED || '', report: f.report, svg: [Math.round(sb2.width), Math.round(sb2.height)],
                            panel: [Math.round(hb.width), Math.round(hb.height)] });
          k++; next();
        });
      })();
    }, 450);
  }
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(function () { setTimeout(run, 60); });
})();
</script>"""


def generic_head(panel):
    """the stylesheets of a generic frame (no course): the tokens, the shell, the kit - and the frame's own few rules"""
    css = [os.path.join(TOKENS, x) for x in ("gb_tokens.css", "gb_shell.css", "gb_compose.css")] + [os.path.join(KIT, "kit.css")]
    if panel == "task":
        css.insert(2, os.path.join(SKILLS, "course-task-ux", "assets", "gb_answer.css"))
    head = "".join('<link rel="stylesheet" href="%s">' % uri(x) for x in css if os.path.isfile(x))
    head += ("<style>body{margin:0;background:var(--grey)} .studio-box{margin:20px auto;display:flex}"
             " .studio-box .kit-fig{height:100%} .studio-task{max-width:1240px;margin:20px auto;padding:20px;background:var(--white)}"
             " .studio-task .ga{width:640px;max-width:100%;position:relative} .studio-task .ga svg{display:block;width:100%;height:auto}"
             " .slide{position:absolute;inset:0;display:flex}"
             " .sheet{display:grid;gap:16px;padding:16px;box-sizing:border-box} .sheet-cell{min-width:0}"
             " .sheet-cap{font:700 15px/1.2 sans-serif;color:var(--navy);height:28px;overflow:hidden;white-space:nowrap}"
             " .sheet .kit-screen{width:100%}</style>")
    return head


# the figure's panel, as the deck shows it, at each window width - the contact sheet draws every step at this width, so the
# words are grown (the 12.5 px floor) exactly as on the real slide
PANEL_W = {1280: 682, 1024: 443}


def sheet_size(spec, size):
    """(cell width, columns, page width, page height) of the contact sheet for a window `size`"""
    cw = PANEL_W.get(size[0], int(size[0] * 0.53))
    n = len(spec.get("steps") or []) + 1
    cols = 1 if n == 1 else 2
    ch = int(round(cw * spec["size"][1] / float(spec["size"][0]))) + 24 + 28            # the panel's padding, the caption
    rows = (n + cols - 1) // cols
    return cw, cols, cols * cw + (cols + 1) * 16, rows * ch + (rows + 1) * 16


def sheet_html(spec, parts_js, size):
    """ONE page that draws the figure at the end of every step side by side (step 0 = the rest state), each in a dark panel the
    width of the real slide's - so one browser run gives the whole sequence, where a --step N run gave one picture"""
    cw, cols, pw, ph = sheet_size(spec, size)
    steps = spec.get("steps") or []
    cells = ""
    for k in range(len(steps) + 1):
        title = "Start" if k == 0 else (steps[k - 1].get("title") or "")
        cells += ('<div class="sheet-cell"><div class="sheet-cap">%s</div><div class="kit-screen"><svg data-kit="#kit-sheet" '
                  'data-sheet-step="%d"></svg></div></div>' % (html.escape("%s" % title if k == 0 else "Step %d - %s" % (k, title)), k))
    data = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    scripts = [os.path.join(KIT, "kit.js")] + ([parts_js] if parts_js else [])
    # each cell is a normal figure (the frame grows as in a deck), moved to its step once it is drawn
    run = ("<script>setTimeout(function(){KIT.figures.forEach(function(f,i){var svg=f.svg,k=+svg.getAttribute('data-sheet-step');"
           "f.go(k,true);f.layout(true);});"
           "if(document.getAnimations)document.getAnimations().forEach(function(a){try{var t=a.effect.getTiming();"
           "if(t.iterations===Infinity)a.pause();else a.finish();}catch(e){}});},400);</script>")
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">%s</head><body><div class="sheet" '
            'style="grid-template-columns:repeat(%d,%dpx);width:%dpx">%s</div><script type="application/json" id="kit-sheet">%s</script>%s%s</body></html>'
            % (generic_head("two-col"), cols, cw, pw, cells, data, "".join('<script src="%s"></script>' % uri(s) for s in scripts), run)), (pw, ph)


def page_html(spec, ctx, panel, parts_js, shot):
    """(html, base folder): the studio page, read from the module's presentation folder (course) or the kit"""
    shot_js = "null" if shot is None else json.dumps(shot)
    probe = PROBE % {"audit": uri(AUDIT), "out": OUT_ID, "shot": shot_js}
    real = None
    if ctx:
        real, mdir, why = real_slide(ctx)
        if not real:
            print("  (drawn in a generic frame: %s)" % why)
    if real:
        head = "".join('<link rel="stylesheet" href="../assets/%s">' % x for x in real["styles"])
        head += "".join('<link rel="stylesheet" href="%s">' % x for x in real["extra"])
        scripts = ["../assets/gb_deck.js", "../assets/gb_fit.js", "../assets/gb_zoom.js", uri(os.path.join(KIT, "kit.js"))]
        local = os.path.join(real["mdir"], "assets", "kit_parts.js")
        if parts_js or os.path.isfile(local):
            scripts.append(uri(parts_js) if parts_js else "../assets/kit_parts.js")
        scripts += ["../" + x for x in ctx["build"].get("scripts", [])]
        # the factory's current kit, not the module's copy: the studio is where a kit change is tried first
        head = head.replace('href="../assets/kit.css"', 'href="%s"' % uri(os.path.join(KIT, "kit.css")))
        body = ('%s<main id="stage">%s</main>%s<script>GBDeck.init({ hooks: window.GB_HOOKS || {} });</script>'
                % (real["chrome"], real["slide"], "".join('<script src="%s"></script>' % s for s in scripts)))
        doc = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><base href="%s/">'
               '<meta name="viewport" content="width=device-width, initial-scale=1">%s</head><body>%s%s</body></html>'
               % (Path(os.path.join(real["mdir"], "presentation")).as_uri(), head, body, probe))
        return doc, real.get("probs") or []
    head = generic_head(panel)
    scripts = [os.path.join(KIT, "kit.js")] + ([parts_js] if parts_js else [])
    body = generic_slide(spec, panel) + "".join('<script src="%s"></script>' % uri(s) for s in scripts)
    doc = ('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
           'initial-scale=1">%s</head><body>%s%s</body></html>' % (head, body, probe))
    return doc, []


class _Run(object):
    """a hidden browser writing what it read back into a file (a pipe left unread while another one finishes made
    the browser stall). 2.57.0: it holds one slot of the computer's pool (browser_slots.py) from its start until
    wait() returns - start one and wait() for it before starting the next in the same thread"""

    def __init__(self, exe, url, size, prof, shot_png=None):
        import browser_slots
        args = [exe, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--mute-audio",
                "--no-default-browser-check", "--user-data-dir=" + prof, "--allow-file-access-from-files",
                "--window-size=%d,%d" % size, "--virtual-time-budget=%d" % (6000 if shot_png else 20000)]
        args += ["--screenshot=" + shot_png] if shot_png else ["--dump-dom"]
        self.out = os.path.join(prof, "dom.html")
        self.slot = browser_slots.slot()
        self.slot.__enter__()
        self.t0, self.what = time.time(), "%s %dx%d" % ("shot" if shot_png else "probe", size[0], size[1])
        try:
            self.fh = io.open(self.out, "w", encoding="utf-8", errors="replace")
            self.p = subprocess.Popen(args + [url], stdout=self.fh, stderr=subprocess.DEVNULL, cwd=prof)
        except BaseException:
            self.slot.__exit__(None, None, None)
            raise

    def wait(self, timeout):
        try:
            self.p.wait(timeout=timeout)
            ok = True
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
            ok = False
        finally:
            self.slot.__exit__(None, None, None)
        self.fh.close()
        text = io.open(self.out, encoding="utf-8", errors="replace").read() if ok else ""
        if os.environ.get("CF_TIMING"):            # 2.61.0: the run's real seconds and the page's own clock
            import cf_timing
            v = re.search(r'&quot;virt&quot;:(\d+)|"virt":(\d+)', text)
            cf_timing.note("studio", self.what, time.time() - self.t0, virt=int(v.group(1) or v.group(2)) if v else None, ok=ok)
        return ok, text


def chrome(exe, url, size, prof, shot_png=None):
    os.makedirs(prof, exist_ok=True)
    return _Run(exe, url, size, prof, shot_png)


def window_for(size, exe=None):
    """the window that gives a page of exactly `size` - the drawing check's own measurement, so both see the same page"""
    sys.path.insert(0, COMPILE)
    import drawing_check
    return drawing_check.window_for(exe or find_browser(), size)


def run(spec_path, parts=None, panel=None, sizes=((1280, 800), (1024, 768)), step="final", out=None, quiet=False,
        shots=True, spec=None, ctx=None):
    """{size: {"states": [...], "report": {...}, "shot": png}} and a list of problems; None, why when it cannot run.
    2.50.0: shots=False only measures (no screenshot run); spec= draws this spec instead of the file's (a candidate fix,
    figure_fit.py), on the file's own slide; ctx= the slide context, when the caller already found it"""
    exe = find_browser()
    if not exe:
        return None, "no Chrome or Edge on this computer (set CF_BROWSER)"
    if spec is None:
        try:
            spec = json.load(io.open(spec_path, encoding="utf-8"))
        except ValueError as err:
            return None, "%s is not valid JSON - %s" % (spec_path, err)
    else:
        spec = json.loads(json.dumps(spec))
    if panel == "task" and not ctx:             # 2.52.1: a spec a course's task question stands on - its real task page
        tctx = task_context(spec_path)
        if tctx:
            return task_page_run(spec_path, spec, tctx, sizes, out, shots)
    ctx = ctx or (course_context(spec_path) if not panel else None)
    if ctx and spec is not None:            # the slide is built from the build sheet's entry with THIS spec in it
        ctx = dict(ctx, spec_override=spec)
    if ctx and not parts:
        cand = os.path.join(ctx["course"], "modules", "module%02d" % ctx["module"], "assets", "kit_parts.js")
        parts = cand if os.path.isfile(cand) else None
    if not spec.get("label"):
        spec["label"] = "studio"
    tmp = tempfile.mkdtemp(prefix="kit_studio_")
    out = out or os.path.join(os.path.dirname(os.path.abspath(spec_path)), "_studio")
    os.makedirs(out, exist_ok=True)
    stem = os.path.basename(spec_path).replace(".kit.json", "")
    res, procs, notes = {}, [], []
    try:
        for size in sizes:
            for mode in ("probe", "shot") if shots else ("probe",):
                sheet = mode == "shot" and step == "all"
                if sheet:                       # ONE page with every step side by side: one browser run for the whole sequence
                    doc, win = sheet_html(spec, parts, size)
                    nts = []
                else:
                    doc, nts = page_html(spec, ctx, panel or "two-col", parts, None if mode == "probe" else step)
                notes += nts
                f = os.path.join(tmp, "%s_%dx%d.html" % (mode, size[0], size[1]))
                io.open(f, "w", encoding="utf-8").write(doc)
                prof = tempfile.mkdtemp(prefix="p_", dir=tmp)
                png = os.path.join(out, "%s_%dx%d%s.png" % (stem, size[0], size[1], "_all" if sheet else "")) if mode == "shot" else None
                # a screenshot's page is its whole window; a page read back (--dump-dom) is smaller than its window
                if not sheet:
                    win = size if png else window_for(size, exe)
                procs.append((size, mode, png, (uri(f), win, png, prof)))

        def go(job):
            # 2.57.0: each browser in a thread of its own, holding one slot of the computer's pool while it runs - a
            # thread never holds one slot while it waits for the next (the runs used to start all at once, then be read)
            size, mode, png, (u, win, shot, prof) = job
            ok, so = chrome(exe, u, win, prof, shot).wait(30)
            if not ok:                                 # a hidden browser that stalls is tried once more, on its own
                if os.environ.get("KIT_STUDIO_DEBUG"):
                    print("  (the %s run at %dx%d stalled - tried again)" % (mode, size[0], size[1]))
                ok, so = chrome(exe, u, win, tempfile.mkdtemp(prefix="p_", dir=tmp), shot).wait(60)
            return ok, so
        import concurrent.futures as cf
        with cf.ThreadPoolExecutor(max_workers=max(1, len(procs))) as ex:
            outs = list(ex.map(go, procs))
        for (size, mode, png, _), (ok, so) in zip(procs, outs):
            key = "%dx%d" % size
            r = res.setdefault(key, {})
            if mode == "shot":
                r["shot"] = png if png and os.path.isfile(png) else None
                continue
            m = re.search(r'<pre id="%s">(.*?)</pre>' % OUT_ID, so or "", re.S)
            if not m:
                r["error"] = "the page did not finish in the hidden browser"
                continue
            try:
                r.update(json.loads(html.unescape(m.group(1))))
            except ValueError:
                r["error"] = "the probe's answer could not be read"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"sizes": res, "context": ctx and {"module": ctx["module"], "screen": ctx["screen"]}, "notes": notes}, None


def problems(result):
    """every finding, once: (size, step, check, part, detail)"""
    seen, out = set(), []
    for size, r in sorted(result["sizes"].items()):
        if r.get("error"):
            out.append((size, "-", "error", r["error"], ""))
            continue
        for st in r.get("states", []):
            if st.get("aborted"):         # the audit did not run on this step - never a clean step
                out.append((size, st.get("step", "-"), "aborted", st["aborted"], "the drawing was not measured"))
            for f in st.get("findings", []):
                key = (size, f["check"], f["part"], f.get("other"))
                if key in seen:
                    continue
                seen.add(key)
                out.append((size, st["step"], f["check"], f["part"], f["detail"] + ((" - " + f["other"]) if f.get("other") else "")))
        rep = r.get("report") or {}
        for u in rep.get("unplaced") or []:
            out.append((size, "-", "label", '"%s" (%s)' % (u["text"], u.get("part") or "?"),
                        "found no clear place - give the figure more room (its size, a part moved), or shorten the words"))
    return out


def summary(result, spec_path, gate="1280x800"):
    """the text, and the findings at the gate size (1280 x 800, the tablet); every other size is stated, not judged"""
    lines = []
    ctx = result.get("context")
    lines.append("Figure studio - %s%s" % (os.path.basename(spec_path),
                                            (" on M%02d %s, its real %s" % (ctx["module"], ctx["screen"], "task page" if ctx.get("page")
                                                                            else "slide")) if ctx else ""))
    for size, r in sorted(result["sizes"].items(), reverse=True):
        rep = r.get("report") or {}
        st = r.get("states") or [{}]
        if r.get("error"):
            lines.append("  %s: %s" % (size, r["error"]))
            continue
        lines.append("  %s: drawn %s px in a %s px panel, scale %.2f, words x%.2f (%s), smallest word %s px, theme %s%s"
                     % (size, "x".join(map(str, st[-1].get("svg", []))), "x".join(map(str, st[-1].get("panel", []))),
                        rep.get("scale") or 0, rep.get("up") or 1,
                        "the 12.5 px floor" if (rep.get("up") or 1) > 1.001 else "1:1 or larger",
                        rep.get("minTextPx"), rep.get("theme"),
                        (", zoomed %.2fx to fill the panel" % rep["zoom"]) if (rep.get("zoom") or 1) > 1.001 else ""))
        lines.append("      labels: %s, %s moved, %s with a leader, %s with no clear place; %d step(s) audited"
                     % (rep.get("labels"), rep.get("moved"), rep.get("leaders"), len(rep.get("unplaced") or []), len(st)))
        if r.get("shot"):
            lines.append("      screenshot: %s" % r["shot"])
    allp = problems(result)
    probs = [x for x in allp if x[0] == gate]
    if gate not in result["sizes"]:       # only the tablet size is judged - without it nothing was, so it is not clean
        probs.append((gate, "-", "not measured", "the tablet size",
                      "was not in --sizes; add %s - only that size is judged" % gate))
    for size, step, check, part, detail in probs:
        lines.append("  - %s step %s: %s - %s %s" % (size, step, check, part, detail))
    other = [x for x in allp if x[0] != gate]
    if other:
        lines.append("  stated, not judged - at the other size(s) the panel is smaller, the words are grown to stay 12.5 px, and:")
        for size, step, check, part, detail in other:
            lines.append("    %s step %s: %s - %s %s" % (size, step, check, part, detail))
    lines.append("%d finding(s) at %s" % (len(probs), gate) if probs else "clean at %s - every step" % gate)
    return "\n".join(lines), probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("spec")
    ap.add_argument("--parts", help="a module's kit_parts.js (found by itself for a spec inside a course)")
    ap.add_argument("--panel", help="two-col | dark | wide-left | task | WxH (default: the real slide, or two-col)")
    ap.add_argument("--sizes", default="1280x800,1024x768")
    ap.add_argument("--step", default="final", help="the step in the screenshot: final, a number, or all (a contact sheet of every step)")
    ap.add_argument("--out", help="where the screenshots go (default: _studio next to the spec)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--inset-over", help="x,y,w: a stand-in photo laid over the drawing in its own units (the deck's \"inset over\"); not with --step all")
    o = ap.parse_args(argv)
    if o.inset_over:
        global INSET_OVER
        INSET_OVER = tuple(float(v) for v in o.inset_over.split(","))
    sizes = tuple(tuple(int(v) for v in s.split("x")) for s in o.sizes.split(","))
    t0 = time.time()
    result, why = run(o.spec, o.parts, o.panel, sizes, o.step if o.step in ("final", "all") else int(o.step), o.out)
    if not result:
        print("Not run: " + why)
        return 2
    text, probs = summary(result, o.spec)
    if o.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    print(text)
    print("(%.1f s)" % (time.time() - t0))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
