# -*- coding: utf-8 -*-
"""build_module.py - a module built and every check run, in ONE command; only what fails is printed (2.50.0).

    python compile/scripts/build_module.py <course> --module 1 [--viewport 1920x1080] [--no-course-pages]
                                           [--no-fix] [--no-review] [--draft] [--force]

WHY (IGF M01 benchmark, 2026-10-19): one module took 6 compiles and about 20 separate check runs, each one a turn of the
model re-reading a context of ~200k tokens. Every check still runs - nothing here is skipped or loosened - but in one
process, the independent ones at once, and the answer is short:

  1  figures      every kit figure on its real slide at once (course-visuals/kit/scripts/figure_fit.py): the spec checks,
                  every drawing audit at every step, grouped per figure; the fixes with one right answer made and proven
  2  compile      compile_module.py (deck, task pages, answer key, plan; its own drawing check, L54, on every page)
  3  the checks   at the same time: check_script_match.py --part instructor and --part trainee, check_navigation.py,
                  run_audits.py (1280 x 800, 1024 x 768 and any --viewport), then compile_course.py and
                  check_course_package.py (the course's own pages and the classroom's importer)
  4  the review   when everything passes: review_sheets.mjs photographs every slide, every figure step and every question
                  (asked, answered wrong, answered right) onto a few sheets - only the screens changed since the last
                  review - and checks that every question grades right and wrong answers as such (compile GUIDE 2f)

  0  (2.52.0) a build sheet that still has --init-build's blanks (a slide with no picture, a question on no picture, a
                  planned 3D scene not written) builds nothing: one line says what to fill (--draft builds anyway)

Printed: each failure with its file, slide or question, and what to do; a figure's problems once per part, not once per
step; then one line - PASS, or how many problems. Everything else is in the full log (its path is the last line), which
ends with each stage's seconds (2.52.0).
--no-course-pages: a module agent in a parallel build (orchestration Rule 3 - one process writes COURSE.html).
A figures-only round (2.56.0): when the last full build failed on nothing but the figures, and the script and the build
sheet are as they were then, a build whose figures still fail stops after them (~1 min, not ~3) - fix the figures in the
studio, run again; once they are clean the whole build runs. --full runs everything every time. PASS is only ever a full run.
2.57.0: the drawing check and the audits judge again only the slides and task pages changed in anything they load since
their last clean check (check_cache.py; the figures already did) - a failing one every time; --full judges everything.
Every hidden browser takes a slot of one pool for the whole computer (browser_slots.py, CF_BROWSER_SLOTS).
2.63.3 (the 2.63.2 full-course run, 4 h 34 min):
  - a module's FIRST build waits its turn behind another module's first build (browser_slots.cold_turn - a queue since
    2.71.0, at most 45 min; --long-pole goes first): wave 1's three first builds overlapped and M01's took 1,076 s;
  - a build that runs past ANSWER_WITHIN (9 min, CF_BUILD_ANSWER_WITHIN) is not lost to the shell's 10-minute limit: it
    goes on by itself and says "STILL BUILDING"; the same command with --wait waits for it and prints its answer (a builder
    whose shell call ended at 600 s waited blind). A second build of a module that is building waits for that one;
  - the review sheets are promoted at MODULE CLEAN (in a parallel build only the course package is left, judged after
    assembly), photographed only for the screens that changed (--shots), and compared with the last REVIEWED sheets
    (review\\MNN_reviewed, written by --reviewed once someone looked at them) - not with the last build's, so no change
    goes unseen when nobody reviewed in between; POLISH.md is kept outside the folder a promotion replaces
    (review\\MNN_POLISH.md - five POLISH lists were deleted in the run).
      build_module.py <course> --module 1 --reviewed     the sheets in review\\MNN were looked at: the next ones show
                                                         only what changes after them
Exit 0 PASS, 1 problems to fix, 2 stopped (the compiler refused: not approved, changed by hand, design files edited),
3 still building (run the same command with --wait), 4 PHASE A CLEAN (2.73.0: every check passed, but picture slots still
hold --init-build's placeholders or a 3D starter - fill them from working_claude\\visuals\\MNN_VISUAL_NEEDS.md, Phase B).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FACTORY = os.path.join(SKILLS, "course-factory", "scripts")
MEASURE = os.path.join(SKILLS, "course-module-ux", "measure", "scripts")
KIT = os.path.join(SKILLS, "course-visuals", "kit", "scripts")
sys.path.insert(0, HERE)
sys.path.insert(0, FACTORY)
sys.path.insert(0, KIT)

PY = sys.executable
L54_TAIL = re.compile(r" \(L54: fix the drawing.*?\)$| \(try the figure in the studio:.*?\)$| \(see every step at once:.*?\)$")


def run(cmd, timeout=900, started=None):
    """(exit code, output) of one tool, run as its own process (as the person would run it)"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        import browser_slots              # 2.62.1: a tool that runs out of time is ended with every browser it started
        p = browser_slots.run_tree(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env,
                                   started=started)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 2, "timed out after %d s: %s" % (timeout, " ".join(cmd))
    except OSError as err:
        return 2, "could not run %s: %s" % (cmd[0], err)


def run_checks(jobs, pkg_cmd, retry=None):
    """the checks at the same time, then the course package once the files it reads are still (it waits for every job but
    the review sheets). -> (results, seconds, retry's answer). retry(key, result), asked as each check ends, says whether
    the round will be built again (2.63.0): then every check still running is ended - the review sheets first, a third of
    a round - and the package is not checked; the next round runs them all (IGF M01 / M02 v262: retried rounds of
    22-824 s waited for sheets and a package check nobody read)."""
    import browser_slots
    results, took, live, again = {}, {}, {}, [None]

    def run_timed(k, c):
        s = time.time()
        r = run(c, started=lambda p: live.__setitem__(k, p))
        live.pop(k, None)
        took[k] = time.time() - s
        return r
    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(run_timed, k, c): k for k, c in jobs.items()}
        pkg = None
        for f in cf.as_completed(futs):
            k = futs[f]
            results[k] = f.result()
            if retry and again[0] is None and not k.startswith("review"):
                again[0] = retry(k, results[k]) or None
                if again[0]:
                    for p in list(live.values()):
                        browser_slots.kill_tree(p.pid)
                        try:
                            p.kill()
                        except OSError:
                            pass
            # the importer reads every file of the module folder: it waits for the audits, whose probe pages come and go
            # in presentation\, and for the course pages; it then runs beside the review sheets
            if again[0] is None and pkg is None and all(x in results for x in jobs if x != "review sheets"):
                pkg = ex.submit(run_timed, "course package", pkg_cmd)
        if again[0] is None:
            if pkg is None:
                pkg = ex.submit(run_timed, "course package", pkg_cmd)
            results["course package"] = pkg.result()
    return results, took, again[0]


def compile_problems(out):
    """the compiler's 'To fix before it is shown' list, and its L60 recommendation"""
    probs, rec = [], ""
    if "To fix before it is shown:" in out:
        tail = out.split("To fix before it is shown:", 1)[1]
        probs = [L54_TAIL.sub("", x[4:].rstrip()) for x in tail.splitlines() if x.startswith("  - ")]
    m = re.search(r"RECOMMENDED \(L60\) - (.*?)\n=+", out, re.S)
    if m:
        rec = " ".join(m.group(1).split())
    return probs, rec


def lines_of(out, n=12):
    keep = [x.rstrip() for x in out.splitlines() if x.strip() and not x.startswith("  note:") and not set(x.strip()) <= set("=-")]
    return keep[-n:]


# the course's own pages - and (2.58.0) what follows from them not existing yet: the importer reads the course's ID and
# title from COURSE.html, so before assembly it says "The course ID must be ..." / "Give the course title." / no
# descriptor; and a sync tool's leftovers beside the modules. None of them is one module's to fix in a parallel build
COURSE_PAGES = re.compile(r"START_HERE|START_COURSE|COURSE\.html|course_map|_course_shell|The course ID must be|"
                          r"Give the course title|course descriptor is missing|\.tmp\.drive|desktop\.ini")


def own_package_findings(code, out, folder):
    """--no-course-pages (a module agent in a parallel build, 2.51.0): the course package is judged on this module alone.
    The course's own pages (COURSE.html, course_map.js, every START_HERE*) are written by compile_course.py once every
    module is in, and another module is another agent's - so a finding about either is left to the orchestrator's check
    after assembly, and only this module's own findings fail it. Before, no module in a parallel build could PASS (the
    start pages are missing until assembly), so none reached its review sheets. Returns (code, out, how many left out)."""
    if code != 1 or "thing(s) to fix" not in out:
        return code, out, 0
    head, rest = out.split("thing(s) to fix", 1)
    body, sep, tail = rest.partition("\nWorth a look")
    items = [x for x in body.splitlines() if x.startswith("  - ")]
    other = re.compile(r"module(?!%s\b)\d\d\b" % re.escape(folder[-2:]))
    keep = [x for x in items if not COURSE_PAGES.search(x) and not (other.search(x) and folder not in x)]
    left = len(items) - len(keep)
    if keep:
        return 1, out, left
    return 0, head.rsplit("\n", 1)[0] + "\nThis module's own package findings: none (%d left to the check after assembly)\n" % left \
        + (sep + tail if sep else ""), left


def starter_blanks(course, module):
    """2.52.0 - what --init-build left for the builder to fill and is still empty: [(screen ids, what to fill)]. Each is a
    problem the compile reports anyway (no picture file, a question on no picture, a planned 3D scene not written); said
    before anything runs, the build that would only have found them is not spent (M01 workflow benchmark run 1: 68 s,
    eight compile problems, all of them blanks)."""
    import content_script as cs
    import compile_module as cm
    bp = cm.build_path(course, module)
    p = cs.paths(course, module)
    if not (os.path.isfile(bp) and os.path.isfile(p["script"])):
        return []
    try:
        build, script = cs.load(bp), cs.load(p["script"])
    except (OSError, ValueError):
        return []                                   # the compile says what is wrong with the file
    screens = build.get("screens") or {}
    mdir, _ = cm.module_folder(course, module)
    figdir = workspace_figdir(course, module)
    pics, ons, scenes = [], [], []
    for s in script.get("screens") or []:
        e = screens.get(s["id"])
        if e is None:
            continue
        fig = (e.get("figure") or "").strip() or ("tiles" if e.get("tiles") else "")   # (merge) "tiles" are its picture too
        if s["kind"] == "slide" and not s.get("recap") and not fig and (s.get("visual_kind") or "none") != "none":
            pics.append(s["id"])
        elif s["kind"] in cs.TASKS and cs.mech(s) in cm.STARTER_ON_PICTURE and not fig:
            ons.append(s["id"])
        elif s["kind"] == "slide" and re.fullmatch(r"m\w+_%s_3d\.html" % re.escape(s["id"]), fig) \
                and not (build.get("declined_3d") or e.get("declined_3d")) \
                and not any(os.path.isfile(os.path.join(d, fig)) for d in (figdir, mdir) if d):
            scenes.append(s["id"] + " (" + fig + ")")
        elif s["kind"] == "slide" and fig.lower().endswith(".kit3d.json") and not (build.get("declined_3d") or e.get("declined_3d")):
            # 2.71.0 - a 3D-kit scene: missing, or still --init-build's starter ("_todo": parts guessed, not placed)
            p = os.path.join(figdir, fig)
            try:
                # 2.73.0 - in a Phase A sheet the starter is built as it is (no agent yet): the module stays PHASE A CLEAN, never
                # PASS, until its parts are placed (phase_a_slots); only a missing scene stops the build
                todo = bool(json.load(io.open(p, encoding="utf-8")).get("_todo")) and not build.get("phase_a")
            except (OSError, ValueError):
                todo = not os.path.isfile(p)
            if todo:
                scenes.append(s["id"] + " (" + fig + ")")
    out = []
    if pics:
        out.append((pics, "its picture: \"figure\" - a photo in assets\\img, a drawing, or a kit spec"))
    if ons:
        out.append((ons, "the drawing or photo the question is answered on: \"figure\" (and its places, \"areas\" / \"labels\")"))
    if scenes:
        out.append((scenes, "the planned 3D scene is not written (a .kit3d.json still the starter: place its parts as on board, "
                            "delete \"_todo\") - build it, or keep the 2D starter (\"_2d\") with the operator's reason in \"declined_3d\""))
    return out


def phase_a_slots(course, module):
    """2.73.0 - the picture slots that still hold Phase A's stand-ins: [(screen id, what)] - a placeholder the build sheet
    names (compile_module.fill_slots), a 3D starter scene whose parts are not placed yet ("_todo" in its spec). While any is
    left the module is never PASS: it is PHASE A CLEAN at best, and the needs file says what to fill"""
    import content_script as cs
    import compile_module as cm
    bp = cm.build_path(course, module)
    try:
        build = cs.load(bp)
    except (OSError, ValueError):
        return []
    figdir = workspace_figdir(course, module)
    out = []
    for sid, e in sorted((build.get("screens") or {}).items()):
        fig = (e.get("figure") or "").strip() if isinstance(e, dict) else ""
        if e.get("placeholder") or cm.PLACEHOLDER_IMG.search(fig):
            out.append((sid, "placeholder picture (%s slot)" % (e.get("placeholder") if isinstance(e.get("placeholder"), str) else "photo")))
        elif fig.endswith(cm.KIT3D_SPEC) and figdir and os.path.isfile(os.path.join(figdir, fig)):
            try:
                if cs.load(os.path.join(figdir, fig)).get("_todo"):
                    out.append((sid, "3D starter scene - parts not placed yet"))
            except (OSError, ValueError):
                pass
    return out


def without_placeholders(code, out):
    """2.73.0 - Phase A: the package check's "is a Phase A placeholder" lines are the state this build is in, not a finding -
    they are taken out of its answer (and its count) before anything else judges it; every other finding still fails it"""
    if code != 1 or "Phase A placeholder" not in out:
        return code, out
    lines = out.splitlines()
    gone = [x for x in lines if x.startswith("  - ") and "Phase A placeholder" in x]
    lines = [x for x in lines if x not in gone]
    out = "\n".join(lines) + "\n"
    out = re.sub(r"(\d+) thing\(s\) to fix", lambda m: "%d thing(s) to fix" % (int(m.group(1)) - len(gone)), out, 1)
    head = out.split("Worth a look", 1)[0]
    return (1 if [x for x in head.splitlines() if x.startswith("  - ")] else 0), out


def write_stages(log, stages, t0, timing=None):
    """2.52.0 - each stage's seconds at the end of the build log: which stage a slow build spent its time in (M01/M02
    workflow benchmark: build runs of 100-400 s, and no way to tell the figures from the audits from the review sheets).
    2.62.1 - and every hidden browser's real seconds (CF_TIMING, on by default): the browser runs per tool and the slowest
    ones - a round of 824 s or 1333 s could not be explained afterwards (IGF M01 / M02 v262). -> the slowest (s, what)"""
    log.write("\n===== stage seconds\n%s\n%-52s %6.0f s\n" % ("\n".join("%-52s %6.0f s" % (k, v) for k, v in stages),
                                                            "total", time.time() - t0))
    if not timing or not os.path.isfile(timing):
        return None
    try:
        import cf_timing
        rows = [json.loads(x) for x in io.open(timing, encoding="utf-8") if x.strip()]
        log.write("\n===== hidden browsers (%s)\n%s\n" % (os.path.basename(timing), cf_timing.summary(timing)))
        slow = sorted(rows, key=lambda r: -(r.get("wall") or 0))[:5]
        log.write("slowest:\n%s\n" % "\n".join("  %6.1f s  %s  %s" % (r.get("wall") or 0, r.get("tool"), r.get("what")) for r in slow))
        return (slow[0].get("wall") or 0, "%s %s" % (slow[0].get("tool"), slow[0].get("what"))) if slow else None
    except (OSError, ValueError, ImportError):
        return None


def stage_line(stages):
    """2.63.2 - each stage's seconds on the build's own answer, PASS or FAIL, not only in the log: the M01 benchmark's
    METRICS had per-stage seconds for a PASS and only the total for a FAIL - the run that most needs explaining"""
    return "Stages: " + " · ".join("%s %.0f s" % (k.split(" (")[0], v) for k, v in stages) if stages else ""


def workspace_figdir(course, module):
    import workspace
    import content_script as cs
    return workspace.claude_path(course, "figures", cs.mid(module))


def inputs_key(course, module):
    """the words and the build sheet as they are now - what everything after the figures is built from"""
    import content_script as cs
    import compile_module as cm
    h = hashlib.sha256()
    for p in (cs.paths(course, module)["script"], cm.build_path(course, module)):
        try:
            h.update(io.open(p, "rb").read())
        except OSError:
            h.update(b"-")
    return h.hexdigest()[:16]


def last_full(logdir, m):
    try:
        return json.load(io.open(os.path.join(logdir, "%s_last.json" % m), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def figures_only_round(fails, full, last, key):
    """stop after the figures? Only when they are all that fails so far, the last full build failed on nothing but
    figures (or drawing findings of the compile), and it was built from these same words and build sheet"""
    return fails == ["figures"] and not full and bool(last.get("only_figures")) and last.get("inputs") == key


def figure_slides(text):
    """the slide ids the figure pre-check already reported (their compile drawing findings say the same thing again)"""
    return set(re.findall(r"^  (s\d+\w*) \(", text, re.M))


LAYOUT_ROUNDS = 2       # 2.62.0: how many times one build builds again the slides it moved for L62 that did not fit


def moved_misfits(deck_html, audit_out):
    """the slides the compiler built another way for L62 (data-varied) that the audit failed: {sid: (shape, ground, words)}.
    No word count tells whether a slide fits another way (IGF M04 s05's 102 words over a photograph spilled 66 px, M05
    s06's 105 beside a 3D model on the left scrolled 22 px): the audit measures it, and the slide is built its next way"""
    bad = set(re.findall(r"slide \d+ \((\w+)\):", audit_out))
    out = {}
    for tag in re.findall(r"<section [^>]*>", deck_html):
        sid = re.search(r'\bdata-script="(\w+)"', tag)
        v = re.search(r'\bdata-varied="([^"|]+)\|([^"|]+)\|(\w+)"', tag)
        if sid and v and sid.group(1) in bad:
            out[sid.group(1)] = v.groups()
    return out


def measure_out(path, misfits):
    """each misfit's layout joins its slide's measured-out list (compile_module.measured_out); a slide whose approved
    words changed starts a new list"""
    try:
        avoid = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        avoid = {}
    for sid, (shape, ground, words) in misfits.items():
        a = avoid.get(sid) or {}
        if a.get("words") != words:
            a = {"words": words, "avoid": []}
        if [shape, ground] not in a["avoid"]:
            a["avoid"].append([shape, ground])
        avoid[sid] = a
    io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(avoid, indent=1, sort_keys=True))


# 2.72.5 - THE LAYOUT PRE-CHECK. WHY (Desktop\IGF_course_2.66_figures\SPEED_ANALYSIS.md): a slide the compiler built
# another way for L62 that did not fit was found only by the deck audit at the END of a build, and the whole module was
# built again (a LAYOUT round: the figures - a moved slide's figure measured and re-fitted in its new column - the
# compile and every check) - 23.5 of IGF M03's 39.5 build-minutes in the 2.72.3 run, 30 of M02's in the 2.66 run 2,
# where s02 / s14 went through it in four builds running. Now, before the figures, the deck is laid out in memory
# (compile_deck, as figure_fit does) and ONLY the slides built another way that the last build did not build so are
# audited, by run_audits.py's own probes at the build's sizes, the whole deck loaded (run_audits --only's way); a misfit
# is measured out at once (MNN_layout_avoid.json, as before) and the deck laid out again, at most LAYOUT_ROUNDS times.
# The audit at the end still judges every slide, and still builds again if one does not fit after all (a figure fitted
# in the build can change its panel). CF_LAYOUT_PRECHECK=off: not run.
# 2.72.5 (its timed run): "the last build built it so" was not enough - a fixer changed only the DRAWING on a slide kept
# its way (M02 s04, M03 s02), it no longer fit, and the round at the end built the module again. A slide is passed over
# only when it was checked fitting as it is now: its whole markup, the drawing in it, kept in MNN_precheck_fit.json
def section_sha(deck_html, sid):
    m = re.search(r'<section [^>]*\bdata-script="%s"[^>]*>.*?</section>' % re.escape(sid), deck_html, re.S)
    return hashlib.sha1(m.group(0).encode("utf-8")).hexdigest()[:16] if m else ""


def varied_new(deck_html, fitted, seen=()):
    """{sid: slide index from 0} - the slides built another way for L62 (data-varied) that were not checked fitting as
    they are now (fitted: {sid: section_sha}), and not checked in this pre-check already (seen: (sid, shape, ground))"""
    out = {}
    for k, (sid, shape, ground, words) in varied_slides(deck_html):
        if (fitted or {}).get(sid) != section_sha(deck_html, sid) and (sid, shape, ground) not in seen:
            out[sid] = k
    return out


def varied_slides(deck_html):
    """[(slide index from 0, (sid, shape, ground, words key))] of the slides built another way for L62"""
    out, k = [], 0
    for tag in re.findall(r"<section [^>]*>", deck_html):
        if not re.search(r'\bclass="[^"]*\bslide\b', tag):
            continue
        sid = re.search(r'\bdata-script="(\w+)"', tag)
        v = re.search(r'\bdata-varied="([^"|]+)\|([^"|]+)\|(\w+)"', tag)
        if sid and v:
            out.append((k, (sid.group(1),) + v.groups()))
        k += 1
    return out


def browser_audit():
    """audit(deck path, size, [slide index]) -> (result, error): run_audits.measure at its own budget, the window's frame
    measured once - None when there is no Chrome or Edge"""
    if MEASURE not in sys.path:
        sys.path.insert(0, MEASURE)
    import run_audits as ra
    from pathlib import Path
    exe, offset = ra.browser(), []
    if not exe:
        return None

    def audit(deck, size, only):
        if not offset:
            offset.append(ra.frame_offset(exe))
        return ra.measure(exe, Path(deck), size, 240000, offset[0], only)     # run_audits.py's own budget
    return audit


def audit_in_memory(deck_html, mdir, sizes, only, audit):
    """the deck as laid out in memory, written beside the real one (its relative paths) for the audit and removed
    again: -> [(size, result, error)], every size at once"""
    import concurrent.futures as cf
    page = os.path.join(mdir, "presentation", "_layout_precheck_%d.html" % os.getpid())
    io.open(page, "w", encoding="utf-8", newline="\n").write(deck_html)
    try:
        with cf.ThreadPoolExecutor(max_workers=len(sizes)) as ex:
            return list(ex.map(lambda s: (s,) + tuple(audit(page, s, sorted(only))), sizes))
    finally:
        try:
            os.remove(page)
        except OSError:
            pass


def slide_order(deck_html):
    """[(slide index from 0, sid, its section)] - every slide of the deck, in order"""
    out = []
    for mt in re.finditer(r"<section [^>]*>.*?</section>", deck_html, re.S):
        tag = re.match(r"<section [^>]*>", mt.group(0)).group(0)
        if re.search(r'\bclass="[^"]*\bslide\b', tag):
            sid = re.search(r'\bdata-script="(\w+)"', tag)
            out.append((len(out), sid.group(1) if sid else "", mt.group(0)))
    return out


def l62_pairs(deck_html):
    """[(the slide before, the slide)] - two slides in a row that look the same (L62), as compile_deck reports them"""
    import compile_module as cm
    secs = slide_order(deck_html)
    return [(a_, b_) for (_, a_, x), (_, b_, y) in zip(secs, secs[1:])
            if cm.layout_key(x) == cm.layout_key(y) and cm.layout_key(y)[0] not in ("task-launch", "recap", "")]


FIT_WORDS = re.compile(r"\b(scrolls|spills|over-filled)\b")


def slide_audit(got, deck_html):
    """{sid: {"fit": [what], "other": [what]}} of the slides an audit measured: fit = its words scroll, spill or over-fill
    the slide (at any size), other = every other finding on it. got = [(size, result, error)]"""
    if MEASURE not in sys.path:
        sys.path.insert(0, MEASURE)
    import run_audits as ra
    ids = {k: sid for k, sid, _ in slide_order(deck_html)}
    out = {}
    for size, res, _ in got:
        tag = "%dx%d" % tuple(size)
        for name, _, _ in ra.PROBES:
            for x in ra.summarise(name, (res or {}).get(name) or {"ABORTED": "no result"})[2]:
                f = re.match(r"^slide (\d+) \((\w+)\): (.*)$", x) or re.match(r"^screen (\d+)() (.*)$", x)
                sid = f and (f.group(2) or ids.get(int(f.group(1)) - 1))
                if sid:
                    out.setdefault(sid, {"fit": [], "other": []})["fit" if FIT_WORDS.search(f.group(3)) else "other"].append(
                        "%s %s" % (tag, f.group(3)))
        for o in (((res or {}).get("deck") or {}).get("res") or {}).get("overfilledSlides") or []:
            sid = ids.get(int(o.get("slide") or 0) - 1)
            if sid:
                out.setdefault(sid, {"fit": [], "other": []})["fit"].append("%s over-filled %s %%" % (tag, o.get("fillPct")))
    return out


def fit_misses(deck_html, audit_out):
    """the slides whose words the build's audits found scrolling, spilling or over-filling (run_audits.py's answer) - the
    next build's pre-check measures them first and the layout solver settles them (2.72.7)"""
    ids = {k: sid for k, sid, _ in slide_order(deck_html)}
    out = set(re.findall(r"slide \d+ \((\w+)\): (?:scrolls|spills)\b", audit_out))
    for line in re.findall(r"over-filled: (.*)", audit_out):
        out |= {ids.get(int(n) - 1) for n in re.findall(r"(\d+) \(\d+ %\)", line)}
    return sorted(x for x in out if x)


# 2.72.7 - THE LAYOUT SOLVER. WHY (Desktop\IGF_course_2.66_figures\NEXT_ROUND.md, the 2.72.5 timed run): of its 53 builds
# 24 failed on a slide whose words scroll or over-fill (M02 s05 in all 20 of M02's) and 29 on an L62 repeat (M03 s10 like
# s09 in 12 running) - the builders searched layouts by hand, a full build (60-180 s) a try. The pre-check now settles
# them before the figures, each try the deck laid out in memory and only the slides it changes audited, at both sizes,
# by run_audits' own probes (a few seconds):
#   words that do not fit - the words' column at the owner's 60 % ("split"), the words in parts (content-in-parts; one
#     part more when they are in parts already), both, then the slide's other ways (L62's, its own measured out);
#   an L62 repeat - the slide BEFORE it built its next way (the repeat's own ways did not fit).
# A try is taken only when the slides it changed fit, no slide looks like its neighbour that did not before and the
# compile finds nothing new. What settles is kept in MNN_layout_avoid.json ("set", beside the ways measured out) while
# the slide's words, picture and sheet are the same (compile_module.fit_key); the build sheet stays the builder's. A try
# that failed is not tried again for those words ("tried"). CF_LAYOUT_PRECHECK=off: not run.
SOLVE_TRIES = 6         # tries a build (each: the deck laid out in memory, ~1-2 s, and one audit at both sizes, ~8-10 s)


def worse(new, old):
    """a try leaves a slide worse than it was: more findings on it, or its drawing's words smaller (the replay of the 2.72.5
    run's M02: a words' column at 60 % settled s04's L62 and took its drawing words from 12 to 10.4 px)"""
    n, o = (new or {}).get("other") or [], (old or {}).get("other") or []
    px = lambda xs: min([float(v) for x in xs if "too small" in x for v in re.findall(r"(\d+(?:\.\d+)?) px", x)] or [99.0])
    return len(n) > len(o) or px(n) < px(o) - 0.3


def parts_in(lines, k):
    """[[lo, hi], ...] - the lines in k parts of about the same words, in order (compile_module.auto_parts' way)"""
    import content_script as cs
    target = sum(cs.wc(x) for x in lines) / float(k)
    parts, cur, acc = [], [], 0
    for i, x in enumerate(lines, 1):
        w = cs.wc(x)
        if cur and acc + w / 2.0 > target and len(parts) < k - 1:
            parts.append(cur)
            cur, acc = [], 0
        cur.append(i)
        acc += w
    parts.append(cur)
    return [[p[0], p[-1]] for p in parts]


def fit_tries(s, b, have, sec):
    """the solver's tries for a slide whose words do not fit: [(what it is, the record's "set")], least change first -
    each changes what is beside the words, never the words. have: what is settled already ("set")"""
    import compile_module as cm
    import content_script as cs
    if not re.search(r'<div class="slide-body two-col', sec):       # words beside a picture: the only kind with a column
        return []
    now, lines = dict(b, **have), cs.lines_of(s.get("text"))
    try:
        split = float(now["split"]) if now.get("split") is not None else cm.LAYOUTS["split"]["default"]
    except (TypeError, ValueError):
        split = cm.LAYOUTS["split"]["default"]
    wider = {"split": cm.SPLIT_HI} if split < cm.SPLIT_HI else {}
    paged, said = {}, ""
    if len(lines) >= 2:
        if 'data-template="content-in-parts.' in sec:
            n = int((re.search(r'data-parts="(\d+)"', sec) or re.search(r"()", "")).group(1) or 0)
            more = parts_in(lines, n + 1) if n else []
            if len(more) > n:
                paged, said = {"parts": more}, "its words in %d parts (\"parts\": %s)" % (len(more), json.dumps(more))
        else:
            paged, said = {"template": "content-in-parts"}, "its words in parts (\"template\": \"content-in-parts\")"
    w = "the words' column at %d %% (\"split\": %g)" % (round(100 * cm.SPLIT_HI), cm.SPLIT_HI)
    out = [(w, dict(have, **wider))] if wider else []
    out += [(said, dict(have, **paged))] if paged else []
    out += [(said + " and " + w, dict(have, **dict(paged, **wider)))] if wider and paged else []
    return out


def solve_layouts(script, build, mdir, figdir, avoid, last, fit, audit, sizes, pairs=None, tries=SOLVE_TRIES, known=None):
    """-> (avoid as it settled, [log lines], {sid: how it settled}, {sid: section_sha} of the slides a taken try measured
    with no finding at all - checked fitting as they are now). fit: the slides whose words do not fit as the pre-check
    measured them, {sid: their other findings}; the L62 repeats are found in the deck laid out (pairs: only these).
    Nothing is written here"""
    import copy
    import compile_module as cm
    screens = {s["id"]: s for s in script.get("screens") or []}
    av = copy.deepcopy(avoid or {})
    laid = {}

    def lay(a):
        """the deck laid out with the record a - once for each record (a compile is 1-2 s, 7 s cold)"""
        k = json.dumps(a, sort_keys=True)
        if k not in laid:
            laid[k] = cm.compile_deck(script, build, mdir, figdir, "CACHE", True, a, last, {})
        return laid[k]
    deck, probs, _ = lay(av)
    other = lambda pr: len([x for x in pr if "looks exactly like the slide before it" not in x])
    lines, done, budget, fits = [], {}, [tries], {}
    base = {sid: {"other": v} for sid, v in fit.items()}        # each slide's findings before the solver (2.72.7: worse())
    base.update({sid: f for sid, f in (known or {}).items() if sid not in base})

    def taken(r, targets):
        """a try taken: the slides it measured with nothing found are checked fitting as they are now"""
        for i in set(targets) | r[3]:
            if i not in r[2]:
                fits[i] = section_sha(r[0], i)
            else:
                fits.pop(i, None)

    def rec(a_, sid):
        """the slide's record in a_, a fresh one when its words, picture or sheet changed since"""
        s = screens[sid]
        k = cm.fit_key(s, (build.get("screens") or {}).get(sid) or {})
        if (a_.get(sid) or {}).get("words") != k:
            a_[sid] = {"words": k, "avoid": []}
        return a_[sid]

    def sec_of(d, sid):
        return next((x for _, i, x in slide_order(d) if i == sid), "")

    def screen(av2, gone=()):
        """a try laid out, not audited: ((deck, probs, changed slides), "") - or (None, why it is not worth an audit: it
        changes nothing, a slide then looks like its neighbour, the compile finds something new). An audit is ~8-10 s, a
        lay-out 1-2 s: the replay of the 2.72.5 run's M02 spent 4 of 8 audits on tries the layout alone ruled out"""
        deck2, probs2, _ = lay(av2)
        cur = {i: x for _, i, x in slide_order(deck)}
        changed = {i for _, i, x in slide_order(deck2) if cur.get(i) != x}
        if not changed:
            return None, "it changes nothing"
        new = set(l62_pairs(deck2)) - (set(l62_pairs(deck)) - set(gone))
        if new:
            return None, "then %s looks like the slide before it (L62)" % ", ".join(b_ for _, b_ in sorted(new))
        if set(gone) & set(l62_pairs(deck2)):
            return None, "still alike"
        if other(probs2) > other(probs):
            return None, "the compile finds something new: %s" % next(x for x in probs2 if x not in probs)[:120]
        return (deck2, probs2, changed), ""

    def measure(pre, targets):
        """the targets and every slide the try changed, audited at every size -> {sid: findings}, None when not measured"""
        budget[0] -= 1
        got = audit_in_memory(pre[0], mdir, sizes, [k for k, i, _ in slide_order(pre[0]) if i in set(targets) | pre[2]], audit)
        return slide_audit(got, pre[0]) if all(res is not None for _, res, _ in got) else None

    def judge(pre, f, targets):
        """'' when the try is good, else why not: words that still do not fit, or a slide left worse than it was (its
        findings before measured once, only when the try found something on it)"""
        look = set(targets) | pre[2]
        bad = sorted(i for i in look if (f.get(i) or {}).get("fit"))
        if bad:
            return "the words still do not fit on %s (%s)" % (", ".join(bad), (f.get(bad[0]) or {}).get("fit", [""])[0])
        unseen = sorted(i for i in look if f.get(i) and i not in base and i in screens)
        if unseen and budget[0] > 0:
            budget[0] -= 1
            got = audit_in_memory(deck, mdir, sizes, [k for k, i, _ in slide_order(deck) if i in unseen], audit)
            if all(res is not None for _, res, _ in got):
                f0 = slide_audit(got, deck)
                base.update({i: f0.get(i) or {} for i in unseen})
        hurt = sorted(i for i in look if f.get(i) and (i not in base or worse(f.get(i), base[i])))
        if hurt:
            return "it leaves %s worse (%s)" % (", ".join(hurt), ((f.get(hurt[0]) or {}).get("other") or ["more findings"])[-1][:90])
        return ""

    def ways(t, n=2):
        """[(what, record)] - the slide's next way, then the one after it (its current ways measured out, one by one)"""
        out, a_ = [], copy.deepcopy(av)
        for _ in range(n):
            key = list(cm.layout_key(sec_of(lay(a_)[0], t)))
            r_ = rec(a_, t)
            if key in r_["avoid"]:
                break
            a_ = copy.deepcopy(a_)
            rec(a_, t)["avoid"].append(key)
            out.append(("its way %s measured out" % "/".join(rec(a_, t)["avoid"][-1]), a_))
        return out

    def with_set(t, st):
        """the record with this settle for t - and the ways measured out beside the old column forgotten (they may fit
        beside this one)"""
        a_ = copy.deepcopy(av)
        r_ = rec(a_, t)
        r_["set"], r_["avoid"] = st, []
        return a_

    # 1 - words that do not fit: a wider column, parts, both - then the slide's other ways
    for sid in [x for x in fit if x in screens]:
        s = screens[sid]
        a0 = rec(copy.deepcopy(av), sid)
        tried = set(a0.get("tried") or [])
        plan = [(w, with_set(sid, st), True) for w, st in fit_tries(s, (build.get("screens") or {}).get(sid) or {},
                                                                  a0.get("set") or {}, sec_of(deck, sid)) if w not in tried]
        if s.get("kind") == "slide" and not s.get("recap"):
            plan += [(w, a_, False) for w, a_ in ways(sid)]
        why = ""
        for what, av2, is_set in plan:
            if budget[0] <= 0:
                lines.append("%s: no tries left in this build (%d) - the next build goes on" % (sid, tries))
                break
            pre, why = screen(av2)
            if pre is None:
                lines.append("tried %s on %s (laid out, not audited): %s" % (what, sid, why))
                continue
            f = measure(pre, [sid])
            if f is None:
                lines.append("%s: not measured - the audit at the end judges every slide" % sid)
                return av, lines, done, fits
            why = judge(pre, f, [sid])
            if not why:
                if rec(av, sid).get("tried"):              # the tries that failed before this one stay tried
                    rec(av2, sid)["tried"] = list(rec(av, sid)["tried"])
                av, deck, probs = av2, pre[0], pre[1]
                taken((pre[0], None, f, pre[2]), [sid])
                done[sid] = what
                lines.append("settled: %s - its words did not fit; %s" % (sid, what))
                break
            lines.append("tried %s on %s: %s" % (what, sid, why))
            if is_set:
                rec(av, sid).setdefault("tried", []).append(what)
        else:
            if sid not in done and plan:
                lines.append("%s: no way found that fits (%s) - fewer words in a part, or a smaller picture beside them"
                             % (sid, why or "every try made before"))
            elif not plan and s.get("kind") == "activity" and not ((build.get("screens") or {}).get(sid) or {}).get("figure") \
                    and (s.get("visual_kind") or "none") != "none":
                # the 2.72.5 run's M02 s05: 20 builds over-filled - a room activity whose script plans a picture
                # (flow_animation) was built with none (--init-build writes no figure for an activity), as a task slide
                # with all its lines; no composition, split or parts changes that layout
                lines.append("%s: no way found that fits - it is a room activity built with no picture, so its %d lines "
                             "stand on the task slide; its script plans one (%s): give it its \"figure\" in the build sheet "
                             "(a kit spec) and it is laid out beside it, its words in parts" % (
                                 sid, len(cm.cs.lines_of(s.get("text"))), s.get("visual_kind")))
    # 2 - an L62 repeat: the slide before it built its next way; then (the 2.72.5 run's M02 s04 / s05: s04's other side did
    # not fit, s05 an activity that never varies) a wider words' column or parts on either, so a side measured out beside
    # the old column may be built again
    # every try laid out first and the ones the layout already rules out dropped (no audit); then the slide with a side
    # measured out and the slide before it built its next way, fewest slides changed first; then the rest
    for prev, sid in [x for x in l62_pairs(deck) if pairs is None or x in pairs]:
        if (prev, sid) not in l62_pairs(deck):
            continue
        cands = []
        for t in (prev, sid):
            st_ = screens.get(t) or {}
            if st_.get("kind") == "slide" and not st_.get("recap"):
                have = rec(copy.deepcopy(av), t)
                cands += [(bool(have.get("avoid")), "%s: %s" % (t, w), with_set(t, st), t)
                          for w, st in fit_tries(st_, (build.get("screens") or {}).get(t) or {}, have.get("set") or {}, sec_of(deck, t))]
        sp = screens.get(prev) or {}
        if sp.get("kind") == "slide" and not sp.get("recap"):
            cands += [(True, "%s, the slide before it: %s" % (prev, w), a_, prev) for w, a_ in ways(prev)]
        ready = []
        for first, what, av2, t in cands:
            pre, why = screen(av2, [(prev, sid)])
            if pre is None:
                lines.append("tried %s for %s's L62 (laid out, not audited): %s" % (what, sid, why))
            else:
                ready.append((not first, len(pre[2]), what, av2, t, pre))
        for _, _, what, av2, t, pre in sorted(ready, key=lambda x: x[:2]):
            if budget[0] <= 0:
                break
            f = measure(pre, [prev, sid])
            if f is None:
                return av, lines, done, fits
            why = judge(pre, f, [prev, sid])
            if not why:
                av, deck, probs = av2, pre[0], pre[1]
                taken((pre[0], None, f, pre[2]), [prev, sid])
                done[sid] = "%s (now %s)" % (what, "/".join(cm.layout_key(sec_of(deck, t))))
                lines.append("settled: %s looked like %s (L62) - %s" % (sid, prev, done[sid]))
                break
            lines.append("tried %s for %s's L62: %s" % (what, sid, why))
    return av, lines, done, fits


def last_misses(logdir, m):
    """the slides whose words the last build's audits found not fitting (MNN_fit_misses.json) - "all" when no build has
    measured them yet (2.72.7: the first build's pre-check measures every slide, the layout solver settles them before the
    figures are fitted to their columns)"""
    try:
        return set(json.load(io.open(os.path.join(logdir, "%s_fit_misses.json" % m), encoding="utf-8")))
    except (OSError, ValueError):
        return "all"


def layout_precheck(course, module, mdir, logdir, m, sizes, audit=None, extra=None):
    """-> ([log lines], {sid: (shape, ground)} measured out). audit(deck path, size, [slide index]) -> (result, error):
    run_audits.measure by default (the test passes its own). extra (2.72.7): slides to audit in the first round besides
    the ones built another way - the last build's misfits, or "all" (no build measured them yet); then the layout solver
    settles what does not fit and every L62 repeat (solve_layouts) - "settled: ..." lines"""
    import workspace
    import content_script as cs
    import compile_module as cm
    if MEASURE not in sys.path:
        sys.path.insert(0, MEASURE)
    import run_audits as ra
    mid_ = cs.mid(module)
    work = workspace.claude_path(course)
    p = cs.paths(course, module)
    script, build = cs.load(p["script"]), cs.load(os.path.join(p["dir"], mid_ + ".build.json"))
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", mid_)
    last = cm.load_layouts(work, mid_)
    fit_path = os.path.join(logdir, "%s_precheck_fit.json" % m)
    try:
        fitted = json.load(io.open(fit_path, encoding="utf-8"))
    except (OSError, ValueError):
        fitted = {}
    lines, out, seen, nofit, known = [], {}, set(), {}, {}
    if audit is None:
        audit = browser_audit()
        if audit is None:
            return ["no Chrome or Edge - not checked (the audit at the end judges every slide)"], {}
    for rnd in range(LAYOUT_ROUNDS + 1):
        deck, _, _ = cm.compile_deck(script, build, mdir, figdir, "CACHE", True, cm.load_layout_avoid(work, mid_), last, {})
        todo = varied_new(deck, fitted, seen)
        if rnd == 0 and extra:
            todo.update({sid: k for k, sid, _ in slide_order(deck) if sid and (extra == "all" or sid in extra)})
        if not todo:
            break
        got = audit_in_memory(deck, mdir, sizes, todo.values(), audit)
        text = []
        for _, res, err in got:
            if res is None:
                lines.append("not measured (%s) - the audit at the end judges every slide" % err)
                return lines, out
            for name, _, _ in ra.PROBES:
                text += ra.summarise(name, res.get(name) or {"ABORTED": "no result"})[2]
        mis = {k: v for k, v in moved_misfits(deck, "\n".join(text)).items() if k in todo}
        found = slide_audit(got, deck)
        known.update({sid: found.get(sid) or {} for sid in todo})
        seen |= {(sid, shape, ground) for _, (sid, shape, ground, _) in varied_slides(deck) if sid in todo}
        own_bad = []
        for sid in todo:                           # what fits as it is now is not checked again until it changes
            f = found.get(sid) or {}
            # 2.72.7 - a slide whose words do not fit, as measured: {sid: (its markup then, its other findings)}
            nofit[sid] = (section_sha(deck, sid), f.get("other") or []) if f.get("fit") else None
            if sid in mis or nofit[sid] is not None:
                fitted.pop(sid, None)
                own_bad += [sid] if sid not in mis and nofit[sid] is not None else []
            else:
                fitted[sid] = section_sha(deck, sid)
        try:
            io.open(fit_path, "w", encoding="utf-8", newline="\n").write(json.dumps(fitted, indent=1, sort_keys=True))
        except OSError:
            pass
        said = ["%s (%s, %s ground)" % (k, v[0], v[1]) for k, v in sorted(mis.items())] + ["%s (its words)" % k for k in sorted(own_bad)]
        lines.append("round %d: %d slide(s) %s checked (%s)%s" % (
            rnd + 1, len(todo), "built another way or not fitting last time" if rnd == 0 and extra else "built another way",
            ", ".join(sorted(todo)), "; did not fit: " + ", ".join(said) if said else " - every one fits"))
        if not mis:
            break
        measure_out(os.path.join(logdir, "%s_layout_avoid.json" % m), mis)
        out.update({k: v[:2] for k, v in mis.items()})
    # 2.72.7 - what still does not fit as it is laid out now, and every L62 repeat, to the layout solver
    avoid = cm.load_layout_avoid(work, mid_)
    deck, _, _ = cm.compile_deck(script, build, mdir, figdir, "CACHE", True, avoid, last, {})
    bad = {sid: v[1] for sid, v in nofit.items() if v is not None and v[0] == section_sha(deck, sid)}
    moved = {sid: k for k, sid, _ in slide_order(deck) if nofit.get(sid) is not None and sid not in bad}
    if moved:                                # did not fit, and built another way since: measured once more as it is now
        got = audit_in_memory(deck, mdir, sizes, moved.values(), audit)
        if all(res is not None for _, res, _ in got):
            found = slide_audit(got, deck)
            known.update({sid: found.get(sid) or {} for sid in moved})
            for sid in moved:
                f = found.get(sid) or {}
                if f.get("fit"):
                    bad[sid] = f.get("other") or []
                elif not f:
                    fitted[sid] = section_sha(deck, sid)
            lines.append("measured again as now built: %s%s" % (", ".join(sorted(moved)), "; did not fit: " + ", ".join(
                sorted(x for x in moved if x in bad)) if set(moved) & set(bad) else " - every one fits"))
    if bad or l62_pairs(deck):
        t = time.time()
        av, said, done, fits = solve_layouts(script, build, mdir, figdir, avoid, last,
                                             {sid: bad[sid] for _, sid, _ in slide_order(deck) if sid in bad}, audit, sizes,
                                             known=known)
        lines += said
        fitted.update(fits)
        if av != avoid:
            try:
                io.open(os.path.join(logdir, "%s_layout_avoid.json" % m), "w", encoding="utf-8", newline="\n").write(
                    json.dumps(av, indent=1, sort_keys=True))
            except OSError:
                pass
        lines.append("the layout solver: %d settled, %.0f s" % (len(done), time.time() - t))
    if moved or bad:
        try:
            io.open(fit_path, "w", encoding="utf-8", newline="\n").write(json.dumps(fitted, indent=1, sort_keys=True))
        except OSError:
            pass
    return lines, out


def check_slides(course, module, sids, sizes, audit=None):
    """--slides s05,s10 (2.72.7): the deck laid out in memory as the next build lays it out (the layouts measured out and
    settled), those slides audited at both sizes, their neighbours compared (L62), the compile's lines on them, and - when
    one does not fit or repeats - what the layout solver would settle. Nothing is written: seconds, not a build.
    WHY (NEXT_ROUND.md): most of the 2.72.5 run's 53 builds were a layout tried by hand; a build is 60-180 s and the agent
    then reads its whole answer. -> (exit code: 0 clean, 1 not, 2 not measured; [lines])"""
    import workspace
    import content_script as cs
    import compile_module as cm
    mid_ = cs.mid(module)
    work = workspace.claude_path(course)
    p = cs.paths(course, module)
    script, build = cs.load(p["script"]), cs.load(os.path.join(p["dir"], mid_ + ".build.json"))
    mdir, _ = cm.module_folder(course, module)
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", mid_)
    avoid, last = cm.load_layout_avoid(work, mid_), cm.load_layouts(work, mid_)
    t0 = time.time()
    deck, probs, _ = cm.compile_deck(script, build, mdir, figdir, "CACHE", True, avoid, last, {})
    order = slide_order(deck)
    idx = {sid: k for k, sid, _ in order}
    lines = ["  %s: not a slide of the deck (its slides: %s)" % (x, ", ".join(i for _, i, _ in order if i)) for x in sids if x not in idx]
    want = [x for x in sids if x in idx]
    if not want:
        return 1, lines
    if audit is None:
        audit = browser_audit()
        if audit is None:
            return 2, lines + ["  no Chrome or Edge - nothing measured"]
    got = audit_in_memory(deck, mdir, sizes, [idx[x] for x in want], audit)
    if any(res is None for _, res, _ in got):
        return 2, lines + ["  not measured: %s" % next(err for _, res, err in got if res is None)]
    found, pairs = slide_audit(got, deck), l62_pairs(deck)
    secs = {sid: x for _, sid, x in order}
    bad, fit = False, {}
    for sid in want:
        t = re.search(r'\bdata-template="([\w-]+)\.v\d+"', secs[sid])
        v = re.search(r'\bdata-variant="([\w-]+)"', secs[sid])
        key = cm.layout_key(secs[sid])
        f = found.get(sid) or {}
        mine = [x for x in probs if "(%s)" % sid in x]
        alike = ["looks like the slide before it, %s (L62)" % a_ for a_, b_ in pairs if b_ == sid] + \
                ["the slide after it, %s, looks like it (L62)" % b_ for a_, b_ in pairs if a_ == sid]
        lines.append("  %s - %s / %s, %s %s: %s" % (sid, t.group(1) if t else "?", v.group(1) if v else "?", key[0], key[1],
                                                    "fits at %s" % " and ".join("%dx%d" % s for s in sizes)
                                                    if not f.get("fit") else "DOES NOT FIT - " + "; ".join(f["fit"][:3])))
        lines += ["    " + x for x in alike + (f.get("other") or [])[:6] + ["compile: " + x[:200] for x in mine[:4]]]
        bad = bad or bool(f.get("fit") or alike or mine or f.get("other"))
        if f.get("fit"):
            fit[sid] = f.get("other") or []
    mypairs = [x for x in pairs if set(x) & set(want)]
    if fit or mypairs:
        _, said, done, _ = solve_layouts(script, build, mdir, figdir, avoid, last, fit, audit, sizes, pairs=mypairs)
        lines += ["  the next build's pre-check: " + x for x in said if x.startswith("settled: ") or "no way found" in x]
        if not done:
            lines.append("  the next build's pre-check settles none of it by itself - change the build sheet (fewer words in a "
                         "part, \"parts\", a smaller picture) and check again")
    lines.append("  (%.0f s; nothing written)" % (time.time() - t0))
    return (1 if bad else 0), lines


def spilled_own(deck_html, audit_out, course, module):
    """2.67.0 - the slides whose OWN layout scrolls or spills at the audit - the compiler's choice (no "template" in the
    build sheet, not built another way for L62), with a picture and more than one line: {slide id: its words key}. Their
    words go in parts at once (compile_module.wants_parts) - on gas M01 (2.65) six slides scrolled at 1024 x 768, each a
    builder's run to put them in parts by hand"""
    # 2.69.0 - and a photograph cropped to a strip: its words in parts give it the height (gas M01 s11, the ship cut through)
    bad = set(re.findall(r"slide \d+ \((\w+)\): (?:scrolls|spills|photo cropped to a strip)\b", audit_out or ""))
    if not bad:
        return {}
    import compile_module as cm
    import content_script as cs
    try:
        script = cs.load(cs.paths(course, module)["script"])
        sheet = cs.load(cm.build_path(course, module)).get("screens") or {}
    except (OSError, ValueError, KeyError):
        return {}
    by_id = {x["id"]: x for x in script.get("screens", [])}
    out = {}
    for tag in re.findall(r"<section [^>]*>", deck_html):
        sid = re.search(r'\bdata-script="(\w+)"', tag)
        if not sid or sid.group(1) not in bad or "data-varied=" in tag or 'data-template="content-in-parts' in tag:
            continue
        sc, b = by_id.get(sid.group(1)), sheet.get(sid.group(1)) or {}
        if not sc or sc.get("kind") != "slide" or b.get("template") or not b.get("figure") or len(cs.lines_of(sc.get("text"))) < 2:
            continue
        # (merge with 2.72.x) the layout record's one key, fit_key - the layout solver and measure_out read it too
        out[sid.group(1)] = cm.fit_key(sc, b)
    return out


def parts_out(path, own):
    """each slide's words go in parts while its words key is the same (compile_module.wants_parts)"""
    try:
        avoid = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        avoid = {}
    for sid, words in own.items():
        a = avoid.get(sid) or {}
        if a.get("words") != words:
            a = {"words": words, "avoid": []}
        a["parts"] = True
        avoid[sid] = a
    io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(avoid, indent=1, sort_keys=True))


def reviewed_dir(out_dir):
    """review\\MNN_reviewed - the manifests of the sheets someone last looked at (--reviewed): what "changed" is judged
    against. Missing: every screen is new to the reviewer"""
    return out_dir + "_reviewed"


def polish_path(out_dir):
    return out_dir + "_POLISH.md"


def promote(pending, out_dir):
    """the new sheets replace the folder of the last ones - and a POLISH.md written into that folder is kept beside it,
    in review\\MNN_POLISH.md (2.63.3: the 2.63.2 run's re-check deleted five builders' POLISH lists this way)"""
    import shutil
    old = os.path.join(out_dir, "POLISH.md")
    if os.path.isfile(old):
        keep = io.open(old, encoding="utf-8", errors="replace").read()
        dest = polish_path(out_dir)
        have = io.open(dest, encoding="utf-8", errors="replace").read() if os.path.isfile(dest) else ""
        if keep.strip() and keep.strip() not in have:
            io.open(dest, "w", encoding="utf-8").write((have.rstrip() + "\n\n" if have.strip() else "") + keep.strip() + "\n")
    shutil.rmtree(out_dir, ignore_errors=True)
    os.replace(pending, out_dir)


def mark_reviewed(out_dir, m):
    """--reviewed: the promoted sheets were looked at - their manifests become the baseline the next sheets are compared
    with, so the next review shows only what changes after this one"""
    import shutil
    man = os.path.join(out_dir, "manifest.json")
    if not os.path.isfile(man):
        print("Nothing to mark: %s has no review sheets yet (build_module.py makes them at module clean)" % out_dir)
        return 1
    base = reviewed_dir(out_dir)
    os.makedirs(base, exist_ok=True)
    for f in ("manifest.json", "manifest_src.json"):
        src = os.path.join(out_dir, f)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(base, f))
        elif os.path.isfile(os.path.join(base, f)):
            os.remove(os.path.join(base, f))
    n = len(json.load(io.open(man, encoding="utf-8")))
    print("Reviewed %s: %d screens - the next review sheets show only what changes after this (%s)" % (m, n, base))
    return 0


# ------------------------------------------------------------------ 2.71.0: the short answer
# WHY (the 2.63.3 M01-M03 run): a failing build answered up to 16,863 characters - every figure finding once per part,
# four hint lines per figure, every audit line - and the builder carried each answer in every later turn (M02's builder:
# 98 M cache-read tokens). The answer now says each problem ONCE with its fix and its file; the full log keeps every line.
FIG_ITEM = re.compile(r"^    ([a-z][a-z ]*?) - (.*)$")
FIG_HEAD = re.compile(r"^  (\w+) \(([^)]+)\) on its slide - drawn \S+ px in a (\S+) px panel, scale ([\d.]+):")
FIG_HINT = {"empty": "crop what no step shows, spread the parts, or a column of the drawing's shape (\"composition\")",
            "text zone": "give the part room for its words (larger w/h, or move it clear)",
            "inside": "move the part into what it sits in, or make the room larger",
            "cut off": "smaller, or a larger frame (\"size\")",
            "small text": "fewer / shorter words in the drawing, or a wider column",
            "label": "more room around that part, or shorter words",
            "contrast": "kit colours for the dark panel",
            "aborted": "the audit did not run on that step - try it in the studio",
            "error": "the figure did not draw - check_kit.py spec, then the studio"}


def short_figures(lines, figrel):
    """figure_fit's report body -> one line per figure and kind of problem, each with its fix; the studio command once"""
    out, fig = [], None

    def flush():
        if not fig:
            return
        sid, name, panel, scale, kinds, extra, same = fig
        out.append("  FIGURE %s - %s (scale %s in a %s px panel): %s%s" % (
            sid, os.path.join(figrel, name), scale, panel, ", ".join("%s x%d" % (k, len(v)) for k, v in kinds.items()),
            " (unchanged since the last build - the same report)" if same else ""))
        for k, v in kinds.items():
            out.append("    %s - e.g. %s - fix: %s" % (k, v[0][:90], FIG_HINT.get(k, "see the full log")))
        out.extend(extra)
        out.append("    try it: course-visuals\\kit\\scripts\\studio.py %s --quick (then one --step all to look)" % os.path.join(figrel, name))
    for line in lines:
        m = FIG_HEAD.match(line)
        if m:
            flush()
            fig = [m.group(1), m.group(2), m.group(3), m.group(4), {}, [], False]
            continue
        if fig and line.startswith("    "):
            it = FIG_ITEM.match(line)
            if line.startswith("        "):                  # the saved candidate's own list: in the full log
                continue
            if line.startswith("    (unchanged since"):
                fig[6] = True
            elif line.startswith("    tried by itself:") and "APPLIED to " in line:      # 2.72.3: the build did it
                fig[5].append("    the closer fit was applied to the spec by the build (%s) - fix only what it lists"
                              % re.search(r"the spec as it was: (.+?\.kit\.json)", line).group(1))
            elif line.startswith("    tried by itself:") and re.search(r"saved as (.+?\.kit\.json)", line):
                fig[5].append("    a closer fit was saved: %s" % re.search(r"saved as (.+?\.kit\.json)", line).group(1)
                              + " - copy it over the spec, then fix what it lists")
            elif line.startswith(("    why EMPTY:", "    the parts named", "    fix (vent):")):
                fig[5].append("    " + line.strip()[:220])
            elif it and it.group(1) not in ("fix", "tried by itself", "try a fix in seconds"):
                fig[4].setdefault(it.group(1), []).append(re.sub(r"\s+\(step [^)]*\)$", "", it.group(2)))
            continue
        flush()
        fig = None
        if line.strip():
            out.append(line[:240])
    flush()
    return out


# ------------------------------------------------------------------ 2.72.7: the stop rule
# WHY (the 2.72.5 timed run, Desktop\IGF_course_2.66_figures\NEXT_ROUND.md): of its 53 builds only 2 passed - M02 and M03
# made 20 builds each re-failing the same few lines (M02 s05 over-filled in all 20, M03 s10 L62 in 12 running), and their
# retry agents (21 / 27 min) ended without PASS on findings the judges and the fix round got anyway. The build itself now
# counts how many builds running printed each finding, and says when the builder's edits have not moved one
STREAK = 3              # the same finding this many builds running: never built for again, listed in the report
STREAK_SKIP = re.compile(r"fixed by itself|waived by \"meaning_ok\"|^  \(a drawing problem|^  \d+x\d+\s+\w+\s+(FAIL|REVIEW)\b")


def finding_keys(say):
    """the answer's findings as keys that stay the same while the finding does: each top-level line (a figure: one per kind
    of problem), without its numbers (px, seconds, counts and sizes move as the builder edits)"""
    keys = []
    for x in say:
        if not re.match(r"^  \S", x) or STREAK_SKIP.search(x):
            continue
        f = re.match(r"^  FIGURE (\S+) - .*?\): (.*?)(?: \(unchanged since.*)?$", x)
        if f:
            keys += ["FIGURE %s: %s" % (f.group(1), re.sub(r" x\d+$", "", k.strip())) for k in f.group(2).split(", ")]
            continue
        k = re.sub(r"\s\(?x\d+\)?|\s*\([\d.\- ]+px\)", "", x.strip())
        k = re.sub(r"(?<![A-Za-z\d])\d+(?:\.\d+)?|(?<=\dx)\d+", "#", k)          # never a slide id's (s05)
        keys.append(" ".join(k.split()))
    return list(dict.fromkeys(keys))


def streak(path, keys):
    """-> {finding: builds running} after this build. A finding counts on while every build prints it, and starts again
    when one does not; a clean build ([] keys) starts every count again"""
    try:
        old = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    new = {k: int(old.get(k) or 0) + 1 for k in keys}
    try:
        io.open(path, "w", encoding="utf-8", newline="\n").write(json.dumps(new, indent=1, sort_keys=True))
    except OSError:
        pass
    return new


def stop_lines(counts, m):
    """the lines the builder stops by (BUILDER_CARD "Stop"): the findings STREAK builds running, and STOP when they are all
    that is left"""
    stuck = [k for k, n in counts.items() if n >= STREAK]
    if not stuck:
        return []
    out = ["SAME FINDING %d BUILDS RUNNING (BUILDER_CARD \"Stop\") - your changes have not moved it: never build for it again, "
           "list it in your report: %s" % (STREAK, "; ".join(stuck[:8]) + (" ..." if len(stuck) > 8 else ""))]
    if len(stuck) == len(counts):
        out.append("STOP - everything this build prints has failed %d builds running: stop building %s and report it (the "
                   "judges and the one fix round take it from here)" % (STREAK, m))
    return out


def short_list(items, width=220):
    """the same line once, with how many times it came ("cut off - circle 43.6 px" twice on one slide is one line)"""
    seen = {}
    for x in items:
        seen[x] = seen.get(x, 0) + 1
    return [(x[:width] + ("..." if len(x) > width else "")) + (" (x%d)" % n if n > 1 else "") for x, n in seen.items()]


AUDIT_LINE = re.compile(r"^\s*(slide \d+ \(\w+\)): (.*)$")


def short_audits(out):
    """run_audits.py's answer -> per viewport and slide, each kind of finding once with its count and the range of px"""
    lines, size, groups, order = [], "", {}, []
    for raw in out.splitlines():
        if raw.startswith("Built "):
            continue
        m0 = re.match(r"^\s*(\d+x\d+)\s+(\w+)\s+(FAIL|PASS|REVIEW)\b(.*)$", raw)
        if m0:
            size = m0.group(1)
            if m0.group(3) != "PASS":
                key = (size, "", raw.strip())
                groups.setdefault(key, [])
                order.append(key)
            continue
        m = AUDIT_LINE.match(raw)
        if m:
            what = m.group(2)
            kind = re.sub(r'"[^"]*"|\d+(\.\d+)?', "", what)
            kind = " ".join(kind.replace("px on screen", "").replace(" by  px", "").split())
            key = (size, m.group(1), kind)
            if key not in groups:
                order.append(key)
            groups.setdefault(key, []).append(what)
            continue
        if raw.strip() and not order:
            lines.append(raw.rstrip())
        elif raw.strip():
            key = (size, "", raw.strip())
            if key not in groups:
                order.append(key)
                groups[key] = []
    for key in order:
        size_, slide, kind = key
        hits = groups[key]
        if not slide:
            lines.append("  " + kind[:200])
            continue
        px = sorted(float(v) for h in hits for v in re.findall(r"(\d+(?:\.\d+)?) px", h))
        rng = (" (%g-%g px)" % (px[0], px[-1]) if px and px[0] != px[-1] else " (%g px)" % px[0] if px else "")
        lines.append("  %s %s: %s%s%s" % (size_, slide, kind, " x%d" % len(hits) if len(hits) > 1 else "", rng)
                     if len(hits) > 1 else "  %s %s: %s" % (size_, slide, hits[0][:200]))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--viewport", action="append", default=[], help="another audit size, WxH (1280x800, 1024x768 and 1280x720 always run)")
    ap.add_argument("--no-course-pages", action="store_true", help="a module agent in a parallel build: no compile_course.py")
    ap.add_argument("--no-fix", action="store_true", help="the figure pre-check makes no fix of its own")
    ap.add_argument("--no-review", action="store_true", help="no review sheets after a pass")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--full", action="store_true", help="never stop after the figures - every stage, every run; the drawing "
                                                        "check and the audits judge every slide and page again (2.57.0)")
    ap.add_argument("--layout-round", type=int, default=0, help=argparse.SUPPRESS)
    ap.add_argument("--reviewed", action="store_true", help="the review sheets were looked at: the next ones show only what "
                                                            "changes after them (2.63.3); builds nothing")
    ap.add_argument("--wait", action="store_true", help="wait for this module's build that said STILL BUILDING and print its "
                                                        "answer (2.63.3)")
    ap.add_argument("--long-pole", action="store_true", help="the course's biggest module (build_order.py, 2.71.0): its first "
                                                             "build never waits for another module's first build")
    ap.add_argument("--full-output", action="store_true", help="print every finding in full, as the log has it (2.71.0: the "
                                                               "answer is one line per problem, with its fix)")
    ap.add_argument("--slides", metavar="s05,s10", help="check only these slides in seconds (2.72.7): the deck laid out in "
                                                         "memory, the slides audited at 1280x800 and 1024x768, their "
                                                         "neighbours compared (L62) - nothing written, nothing built")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--auto", action="store_true", help="2.73.0 Phase B with no agent: at PHASE A CLEAN, each slide's photo slot "
                                                       "whose course-catalogue pick is good enough takes it, and the module is "
                                                       "built again once (visual_needs.py fill --auto)")
    ap.add_argument("--auto-round", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--no-precheck", action="store_true", help="skip the pre-check (precheck.py: missing pictures, photographs "
                                                               "under 800 px, dense text with no picture ...) - 2.65.0")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    import workspace
    import content_script as cs
    course = workspace.work_folder(o.course, create=False)
    import compile_module as cm
    mdir, why = cm.module_folder(course, o.module)
    if not mdir:
        print("Stopped - " + why)
        return 2
    m = cs.mid(o.module) if str(o.module).isdigit() else str(o.module)
    logdir = workspace.claude_path(course, "_build")
    os.makedirs(logdir, exist_ok=True)
    import cf_timing                 # 2.65.0 - the module's clock (gold standard 30-40 min), if --init-build did not start it
    if o.layout_round == 0:
        cf_timing.clock_start(course, m, since="its first build run")
    out_dir = workspace.claude_path(course, "review", m)
    if o.reviewed:
        return mark_reviewed(out_dir, m)
    if o.slides:                     # 2.72.7: a slide check in seconds - nothing built, nothing written
        sizes = [(1280, 800), (1024, 768)] + [tuple(int(x) for x in v.split("x")) for v in o.viewport
                                              if v not in ("1280x800", "1024x768")]
        code, lines = check_slides(course, o.module, [x.strip() for x in o.slides.split(",") if x.strip()], sizes)
        print("SLIDES %s - %s (laid out in memory as the next build lays it out):" % (m, "clean" if code == 0 else "NOT CLEAN"
                                                                                       if code == 1 else "not measured"))
        print("\n".join(lines))
        return code
    blanks = [] if o.draft else starter_blanks(course, o.module)
    if blanks:                       # 2.52.0: nothing is built on a sheet with the starter's blanks in it
        print("FAIL %s - nothing built: the build sheet %s still has the starter's blanks - fill %s (or let Phase A hold "
              "them: compile_module.py <course> --module %s --fill-slots, 2.73.0)"
              % (m, os.path.basename(cm.build_path(course, o.module)),
                 "; ".join("%s: %s" % (", ".join(ids), what) for ids, what in blanks), o.module))
        return 1
    # 2.65.0 - the pre-check: what would fail the build or make it look poor, found in a second from the files alone
    # (precheck.py) - a missing picture, a photograph under 800 px, dense text with no picture - before the figures stage,
    # the slowest one, is spent on a build that could not pass (owner, 2026-10-26: "cut time and usage, quality the same")
    pre_notes = []
    if str(o.module).isdigit() and o.layout_round == 0 and not o.draft:
        # 2.73.2 (owner, 2026-10-28) - the course's small pictures are reused, made sharp on THIS computer first (Real-ESRGAN,
        # once per picture, nothing sent anywhere; a picture with words keeps the plain enlargement); not installed: as before
        up = os.path.join(SKILLS, "course-visuals", "scripts", "upscale_photos.py")
        if os.path.isfile(up) and os.environ.get("CF_UPSCALE", "").lower() != "off":     # off: a test, the same on every PC
            ucode, uout = run([PY, up, course, "--modules", str(int(o.module))], timeout=1800)
            if ucode == 0 and re.search(r"\benlarged\b|made sharp", uout, re.I):
                print("Photographs made sharp on this computer first (upscale_photos.py, Real-ESRGAN)")
    if not o.no_precheck and str(o.module).isdigit() and o.layout_round == 0:
        import precheck
        # a module built before is a rebuild: the small pictures it already has are notes (fix/GUIDE.md 3b)
        # 2.73.0: a deck Phase A built is no rebuild until the module has PASSED - else Phase B's new pictures under 800 px
        # would pass as "pictures it already had" (bench M11: three went in that way)
        try:
            was_passed = bool(json.load(io.open(os.path.join(logdir, "%s_clock.json" % m), encoding="utf-8")).get("passed"))
        except (OSError, ValueError):
            was_passed = False
        try:
            phase_a = bool(cs.load(cm.build_path(course, o.module)).get("phase_a"))
        except (OSError, ValueError):
            phase_a = False
        built = os.path.isfile(os.path.join(mdir, "presentation", "index.html"))
        must, pre_notes = precheck.check(course, o.module, rebuild=built and (was_passed or not phase_a))
        if must:
            print("FAIL %s - nothing built: the pre-check found %d thing(s) to fix first (precheck.py; --no-precheck skips it)"
                  % (cs.mid(o.module), len(must)))
            print("\n".join("  - " + x for x in must))
            print("\n".join("  note: " + x for x in pre_notes or []))
            return 1
    slots_left = [] if o.draft else phase_a_slots(course, o.module)      # 2.73.0 - Phase A: placeholders still in
    # 2.62.1 - every hidden browser of this build writes its real seconds (cf_timing.py); a round the layout retry
    # replaces keeps its own log (_build\M01_build.round1.log) - both were lost when a round was slow (IGF M02 v262)
    timing = os.environ.get("CF_TIMING") or os.path.join(logdir, "%s_timing.jsonl" % m)
    if not os.environ.get("CF_TIMING") or o.layout_round == 0:
        os.environ["CF_TIMING"] = timing
        if o.layout_round == 0:
            for old in [timing] + [os.path.join(logdir, "%s_build.round%d.log" % (m, k)) for k in range(1, LAYOUT_ROUNDS + 1)]:
                try:
                    os.remove(old)
                except OSError:
                    pass
    log = io.open(os.path.join(logdir, "%s_build.log" % m), "w", encoding="utf-8")
    say, fails, notes = [], [], ["Pre-check: " + x for x in pre_notes or []]
    stages = []                      # 2.52.0: (stage, seconds) - written into the log, so a slow stage is seen

    def logged(title, out):
        log.write("\n===== %s\n%s\n" % (title, out))

    def timed(title, since):
        stages.append((title, time.time() - since))
        return time.time()

    # 2.72.5 - the slides built another way for L62 are audited before anything is built (layout_precheck); its seconds
    # are a stage of their own, the figures' clock starts after it
    t_fig = t0
    if o.layout_round == 0 and not o.draft and str(o.module).isdigit() and os.path.isdir(os.path.join(mdir, "presentation")) \
            and (os.environ.get("CF_LAYOUT_PRECHECK") or "").lower() not in ("off", "0", "no"):
        try:
            pre_lines, pre_out = layout_precheck(course, o.module, mdir, logdir, m,
                                                 [(1280, 800), (1024, 768)] + [tuple(int(x) for x in v.split("x")) for v in o.viewport
                                                                              if v not in ("1280x800", "1024x768")],
                                                 extra=last_misses(logdir, m))
        except Exception as err:                     # noqa: BLE001 - the audit at the end still judges every slide
            pre_lines, pre_out = ["could not run (%s) - the audit at the end judges every slide" % err], {}
        logged("layout pre-check (L62)", "\n".join(pre_lines) or "no slide built another way that the last build did not build so")
        t_fig = timed("layout pre-check (L62)", t0)
        if pre_out:
            notes.append("LAYOUT (pre-check) - %d slide(s) built another way so no two neighbours look alike (L62) did not "
                         "fit and are built their next way: %s (kept in %s_layout_avoid.json while their words are unchanged)"
                         % (len(pre_out), ", ".join("%s (%s, %s ground)" % (k, v[0], v[1]) for k, v in sorted(pre_out.items())), m))
        # 2.72.7 - what the layout solver settled, said once: nothing for the builder to copy
        notes += ["LAYOUT (pre-check) - %s (kept in %s_layout_avoid.json while its words, picture and sheet are unchanged; "
                  "nothing to copy)" % (x[len("settled: "):], m) for x in pre_lines if x.startswith("settled: ")]
        notes += ["LAYOUT (pre-check) - " + x for x in pre_lines if ": no way found that fits" in x]
    # 2.63.3 - a module's first build (never built here: no _last.json) measures every figure and tries every fix: one at a
    # time on the computer, the others wait their turn (a queue, 2.71.0) - held through the figures and the compile
    cold = contextlib.ExitStack()
    if o.layout_round == 0 and not os.path.isfile(os.path.join(logdir, "%s_last.json" % m)):
        import browser_slots
        waited = cold.enter_context(browser_slots.cold_turn(first=o.long_pole))
        log.write("\n===== first build: waited %.0f s for another module's first build (browser_slots.cold_turn)\n" % waited)
        if waited >= 5:
            notes.append("First build: waited %.0f s for another module's first build to finish its figures (one at a time)" % waited)
    # 1 - every figure at once, before the compile. 2.54.0 (built as 2.52.0 on its own branch): the module's design files are made the factory's first (the
    # compile does it too) - the figures are measured on their real slide with the module's own gb_compose.css, and a deck
    # built by a newer compiler (the figure first in the markup, .dom-fig) measured with the older style file puts the
    # figure in the wrong column. A file edited inside the module is left alone here; the compile stops on it
    if os.path.isdir(mdir):
        try:
            cm.ensure_design(mdir)
        except Exception:                            # noqa: BLE001 - the compile checks the design files again and says why
            pass
    fig_text = ""
    if str(o.module).isdigit():
        try:
            import figure_fit
            fcode, fig_text, _ = figure_fit.run_all(course, o.module, fix=not o.no_fix, full=o.full)
        except Exception as err:                     # noqa: BLE001 - the compile's own drawing check still runs
            fcode, fig_text = 1, "Figures: the pre-check could not run (%s) - the compile's drawing check still judges them" % err
        logged("figures (figure_fit.py)", fig_text)
        body = [x for x in fig_text.splitlines()[1:-1]]
        if body:
            say.append("FIGURES")
            say += body if o.full_output else short_figures(body, workspace_figdir(course, o.module))
        if fcode:
            fails.append("figures")
    t = timed("figures (figure_fit.py)", t_fig)
    key = inputs_key(course, o.module)
    last = last_full(logdir, m)
    if figures_only_round(fails, o.full, last, key):
        # 2.56.0 - a figures-only round: everything else passed on the last full build, from these same words and build
        # sheet; the compile and the checks are run again once the figures are clean (a fix in a spec moves only its figure)
        write_stages(log, stages, t0)
        log.close()
        print("\n".join(say))
        print("FAIL %s - figures (%.0f s; a figures-only round: the rest passed on the last full build and the script and build "
              "sheet are unchanged - fix these in the studio, run again; the full build runs once they are clean, --full now)"
              % (m, time.time() - t0))
        print(stage_line(stages))
        if not o.no_fix:                         # 2.72.7: a check (QA's --no-fix) is no build of the builder's
            for x in stop_lines(streak(os.path.join(logdir, "%s_streak.json" % m), finding_keys(say)), m):
                print(x)
        print("Full log: %s" % log.name)
        return 1
    # 2 - the compile (with its own drawing check)
    cmd = [PY, os.path.join(HERE, "compile_module.py"), course, "--module", str(o.module)]
    cmd += ["--draft"] if o.draft else []
    cmd += ["--force"] if o.force else []
    cmd += ["--full"] if o.full else []          # 2.57.0: the drawing check judges every slide and page, not only the changed
    ccode, cout = run(cmd)
    logged("compile_module.py", cout)
    t = timed("compile (compile_module.py, its drawing check)", t)
    cold.close()                                 # the next module's first build may start
    if ccode == 2:
        write_stages(log, stages, t0)
        print("\n".join(say + ["", "COMPILE - stopped:"] + ["  " + x for x in lines_of(cout, 25)]))
        print("Full log: %s" % log.name)
        log.close()
        return 2
    probs, rec = compile_problems(cout)
    # every compile problem a drawing finding - the figures above again, or a task page's figure judged here: still a
    # figures-only build (2.56.0). Judged on the whole list, before the figures' repeats are taken out of it
    drawing_only = ccode == 1 and bool(probs) and all(re.search(r"\b(empty|text zone|inside|cut off|small text|label|contrast|"
                                                                r"photo over drawing|scrolls)\b|: inset - ", x) for x in probs)
    shown = figure_slides(fig_text)
    probs = [x for x in probs if not any(re.search(r"\(%s\)[ :]" % re.escape(s), x) and re.search(r"\b(empty|text zone|inside|"
                                                                                                    r"cut off|small text|label|contrast)\b", x)
                                         for s in shown)]
    # 2.66.0 - drawings still to fix: no layout round this build (the timed gas M02 build's first run spent 447 s building
    # again the slides of four drawings its builder was about to redraw - a drawing that changes moves its slide anyway)
    drawings_open = "figures" in fails or any(re.search(r"\b(empty|text zone|inside|cut off|small text|label|contrast|"
                                                        r"photo over drawing|scrolls)\b", x) for x in probs)
    if ccode != 0 or probs:
        fails.append("compile")
        say.append("COMPILE - %d problem(s) to fix%s:" % (len(probs), " (the figures above not repeated)" if shown else ""))
        say += ["  - " + x for x in (probs if o.full_output else short_list(probs))]
        if any("L54" in x or "drawing" in x for x in probs):
            say.append("  (a drawing problem: fix the drawing, or mark a crossing that is meant data-may-cross / data-no-contain / "
                       "data-may-overlap; a kit figure: studio.py <figure>.kit.json --step all)")
    if "Not checked:" in cout:
        fails.append("drawing check not run")
        say.append("DRAWING CHECK did not run: " + cout.split("Not checked:", 1)[1].strip().splitlines()[0])
    if rec:
        notes.append("RECOMMENDED (L60): " + rec)
    mm = re.search(r"Real photographs still missing.*?listed in\s*\n\s*(\S.*?)\n((?:  - .*\n?)*)", cout)
    if mm:
        notes.append("Pictures still missing (found or generated - never taken, 2.73.2): %d thing(s), listed in %s" % (len(mm.group(2).strip().splitlines()), mm.group(1).strip()))
    # 2.52.0 - the compile's notes on pictures: left out of the package, and real photos a task question could stand on
    ml = re.search(r"Pictures no page shows - left out of the package.*?\n((?:  - .*\n?)*)", cout)
    if ml:
        notes.append("Left out of the package (no page shows them; kept in assets\\img\\_unused\\): " +
                     ", ".join(x.strip()[2:] for x in ml.group(1).strip().splitlines()))
    mt = re.search(r"Real photographs a task question could be answered on.*?\n((?:  - .*\n?)*)", cout)
    if mt:
        rows = [re.search(r"\((\w+), [\w_]+\): the real photograph (\S+)", x) for x in mt.group(1).strip().splitlines()]
        notes.append("NOTE - a real photograph could carry: " + ", ".join("%s (%s)" % (r.group(1), r.group(2)) for r in rows if r)
                     + " - the build-sheet lines are in the full log (compile_module.py)")
    # 2.63.0 - the compiler's own notes: words past their layout's measured budget, an inset moved under the words
    notes += list(dict.fromkeys(x.strip()[6:] for x in cout.splitlines() if x.startswith("Note: ")))
    # 3 - the checks, at the same time
    deck = os.path.join(mdir, "presentation", "index.html")
    jobs = {
        # --module-dir (2.58.0): the folder this build resolved - for "final" check_script_match looked in modules\mfinal
        "words (instructor)": [PY, os.path.join(FACTORY, "check_script_match.py"), course, "--module", str(o.module), "--part", "instructor",
                               "--module-dir", mdir],
        "words (trainee)": [PY, os.path.join(FACTORY, "check_script_match.py"), course, "--module", str(o.module), "--part", "trainee",
                            "--module-dir", mdir],
        "navigation": [PY, os.path.join(MEASURE, "check_navigation.py"), mdir],
    }
    # 2.69.0 - 1280x720 too: a 16:9 laptop at 150 % (1920x1080) or a 720p projector - the gas course's M01 s15 table cut
    # its own headings and step names there, and 1280x800 / 1024x768 both passed it (owner's screenshots, 2026-10-27)
    sizes = ["1024x768", "1280x720"] + [v for v in o.viewport if v not in ("1280x800", "1024x768", "1280x720")]
    if os.path.isfile(deck):
        # 2.57.0 - a slide audited clean and unchanged in everything it loads is not measured again (--full: every slide)
        a = [PY, os.path.join(MEASURE, "run_audits.py"), deck, "--quiet", "--cache", os.path.join(logdir, "%s_audits_clean.json" % m)]
        a += ["--full"] if o.full else []
        a += ["--slots", os.path.join(logdir, "%s_slots.json" % m)]          # 2.73.0: each picture slot's real px size
        for v in sizes:
            a += ["--viewport", v]
        jobs["audits 1280x800 %s" % " ".join(sizes)] = a

    if not o.no_course_pages:
        jobs["course pages (compile_course.py)"] = [PY, os.path.join(HERE, "compile_course.py"), course]
    # 4 - the review sheets are made at the same time (2.50.1: they were a third of a passing build), into a folder of
    # their own: they become the review only when everything passes, so a failed build never hides a changed screen
    # 2.63.3: compared with the last REVIEWED sheets, and a screen unchanged since its last picture is not photographed again
    pending = out_dir + ".pending"
    want_review = not o.no_review and not fails
    if want_review:
        import shutil
        shutil.rmtree(pending, ignore_errors=True)
        jobs["review sheets"] = ["node", os.path.join(MEASURE, "review_sheets.mjs"), mdir, pending, "--base=" + reviewed_dir(out_dir),
                                 "--shots=" + os.path.join(logdir, "%s_shots" % m)] + (["--grade-only"] if slots_left else [])
    pkg_cmd = [PY, os.path.join(FACTORY, "check_course_package.py"), os.path.join(course, workspace.MODULES)]
    ak = next((k for k in jobs if k.startswith("audits")), None)

    def will_retry(k, res):
        """the audits failed a slide the compiler built another way for L62: this round is built again (2.62.0)"""
        if k != ak or res[0] == 0 or o.layout_round >= LAYOUT_ROUNDS or not os.path.isfile(deck) or drawings_open:
            return None
        return moved_misfits(io.open(deck, encoding="utf-8").read(), res[1])
    results, took, early = run_checks(jobs, pkg_cmd, will_retry)
    t = timed("the checks, at the same time (wall clock)", t)
    if ak in results and os.path.isfile(deck):    # 2.72.7: the slides whose words did not fit - the next pre-check's first
        try:
            io.open(os.path.join(logdir, "%s_fit_misses.json" % m), "w", encoding="utf-8").write(
                json.dumps(fit_misses(io.open(deck, encoding="utf-8").read(), results[ak][1])))
        except OSError:
            pass
    stages += [("  " + k, took[k]) for k in list(jobs) + ["course package"] if k in took]
    if early:
        # 2.63.0 - the round is built again: what the checks found on the slides is said; the review sheets and the
        # package check that were ended (or never started) run in the next round
        code, out = results[ak]
        logged(ak, out)
        fails.append(ak)
        say.append("%s - FAIL:" % ak.upper())
        say += short_audits(out) if not o.full_output else \
            ["  " + x for x in lines_of("\n".join(y for y in out.splitlines() if not y.startswith("Built ")), 40)]
        stopped = sorted(k for k in jobs if k not in took or k == "review sheets") + ["course package"]
        log.write("\n===== ended early - this round is built again: %s\n" % ", ".join(stopped))
    if early is None and slots_left and "course package" in results:
        results["course package"] = without_placeholders(*results["course package"])
    if early is None and o.no_course_pages:
        pcode, pout, left = own_package_findings(*results["course package"], folder=os.path.basename(mdir))
        if left and pcode != 0:
            # the module's own findings fail it; the left-out ones are only listed in the log
            pout += "\n(%d of the findings above concern the course's own pages or another module - the check after assembly's)\n" % left
        results["course package"] = (pcode, pout)
        if left:
            notes.append("Course package: %d finding(s) about the course's own pages or other modules left to the check after "
                         "assembly (compile_course.py, then check_course_package.py)" % left)
    for k in ([x for x in jobs if x != "review sheets"] + ["course package"]) if early is None else []:
        code, out = results[k]
        logged(k, out)
        if code != 0:
            fails.append(k)
            say.append("%s - FAIL:" % k.upper())
            # the audits name every element and its words (run_audits.summarise), so they keep more lines - no --json run to find them
            if k.startswith("audits") and not o.full_output:      # 2.71.0: per slide, each kind once with its count
                say += short_audits(out)
            else:
                say += ["  " + x for x in lines_of("\n".join(y for y in out.splitlines() if not y.startswith("Built ")),
                                                   40 if k.startswith("audits") else 12)]
    # 2.62.0 - a slide the compiler built another way for L62 that the audit found does not fit is measured out and built
    # its next way, at once: the builder never pins a layout by hand for what the compiler chose
    if ak in fails and drawings_open and o.layout_round < LAYOUT_ROUNDS and os.path.isfile(deck):
        held = moved_misfits(io.open(deck, encoding="utf-8").read(), results[ak][1])
        if held:
            say.append("LAYOUT - %d slide(s) built another way for L62 did not fit (%s): built their next way once the drawings "
                       "pass - not now, while drawings are still to fix (2.66.0)" % (len(held), ", ".join(sorted(held))))
    if ak in fails and not drawings_open and o.layout_round < LAYOUT_ROUNDS and os.path.isfile(deck):
        page_ = io.open(deck, encoding="utf-8").read()
        mis = early or moved_misfits(page_, results[ak][1])
        own = {} if early else spilled_own(page_, results[ak][1], course, o.module)
        if mis or own:
            if mis:
                measure_out(os.path.join(logdir, "%s_layout_avoid.json" % m), mis)
            if own:
                parts_out(os.path.join(logdir, "%s_layout_avoid.json" % m), own)
                print("PARTS - %d slide(s) whose own layout spilled at the audit: %s - built again with their words in parts "
                      "(content-in-parts; kept while their words are unchanged)" % (len(own), ", ".join(sorted(own))))
            log.write("\n===== this round's findings (the build runs again for the slides above)\n%s\n" % "\n".join(say))
            write_stages(log, stages, t0, timing)
            log.close()
            os.replace(log.name, os.path.join(logdir, "%s_build.round%d.log" % (m, o.layout_round + 1)))
            if mis:
                print("LAYOUT - %d slide(s) built another way so no two neighbours look alike (L62) did not fit: %s - built "
                      "again their next way (%.0f s; kept in %s_layout_avoid.json while their words are unchanged)"
                      % (len(mis), ", ".join("%s (%s, %s ground)" % (k, v[0], v[1]) for k, v in sorted(mis.items())),
                         time.time() - t0, m))
            sys.stdout.flush()
            return main(list(sys.argv[1:] if argv is None else argv) + ["--layout-round", str(o.layout_round + 1)])
    passed = not fails
    # 2.63.3 - MODULE CLEAN: in a parallel build (--no-course-pages) everything but the course package passed - the package is
    # judged after assembly. The sheets are promoted then too: before, nothing in a parallel build ever promoted, and the
    # builders re-read stale sheets (IGF M09 re-reviewed a sheet from before its fix)
    clean = passed or (o.no_course_pages and fails == ["course package"])
    review = ""
    if want_review and clean and "review sheets" in results:
        rcode, rout = results["review sheets"]
        if rcode == 0 and not slots_left:        # the sheets are the review now: the last review's folder is replaced
            promote(pending, out_dir)
            rout = rout.replace(pending, out_dir)
        logged("review_sheets.mjs", rout)
        if rcode == 1:                          # not promoted: the next review still compares with the last one shown
            passed = False
            fails.append("task pages")
            say.append("TASK PAGES - FAIL (review_sheets.mjs answered every question by its own keys and checked every leader "
                       "line as the engine placed it - fix the drawing or the build sheet's \"labels\"):")
            say += ["  " + x for x in rout.splitlines() if "FAIL" in x]
        elif rcode == 0 and slots_left:          # 2.73.0 Phase A: graded only - the sheets wait for the real pictures
            pass
        elif rcode == 0:
            first = rout.strip().splitlines()[0] if rout.strip() else ""
            n = re.search(r"Review sheets: (\d+) of (\d+) screens.*?on (\d+) sheet", first)
            review = (("VISUAL REVIEW (required, GUIDE 2f): %s of %s screens changed since the last review, on %s sheet(s) in\n  %s\n"
                       "  Give the sheets to ONE review subagent (model haiku or sonnet) with %s - it returns a short verdict;\n"
                       "  then mark them looked at: build_module.py <course> --module %s --reviewed (in a whole-course workflow the "
                       "QA agent does this review, not the builder)"
                       % (n.group(1), n.group(2), n.group(3), out_dir, os.path.join(SKILLS, "course-factory", "compile", "REVIEW_PROMPT.md"),
                          o.module))
                      if n and n.group(1) != "0" else
                      "Visual review: no screen changed since the last review - nothing new to look at.")
        else:
            notes.append("Review sheets not made (%s) - do the visual review by hand (GUIDE 2f)" % (lines_of(rout, 1) or ["?"])[0])
    slowest = write_stages(log, stages, t0, timing)
    log.close()
    if slowest and slowest[0] > 60:      # 2.62.1: one hidden browser for over a minute - a stalled page or a loaded PC
        notes.append("SLOW: one hidden browser took %.0f s (%s) - a page that barely settles, or a busy computer; the "
                     "build log lists the slowest runs" % slowest)
    try:                                   # what the next run may skip (2.56.0 - a figures-only round)
        io.open(os.path.join(logdir, "%s_last.json" % m), "w", encoding="utf-8").write(json.dumps(
            {"inputs": key, "fails": fails,
             "only_figures": bool(fails) and set(fails) <= {"figures", "compile"} and ("compile" not in fails or drawing_only)}))
    except OSError:
        pass
    for x in say:
        print(x)
    for x in notes:
        print(x)
    secs = time.time() - t0
    needs = ""
    if slots_left or os.path.isfile(os.path.join(workspace.claude_path(course, "visuals"), "%s_VISUAL_NEEDS.json" % m)):
        try:                                             # 2.73.0 - what Phase B fills, with each slot's measured size
            import visual_needs
            needs = visual_needs.write(course, o.module)
        except Exception as why:                         # noqa: BLE001 - the needs file is a help, never a stop
            needs = "the needs file could not be written: %s" % why
    if passed and slots_left and o.auto and not o.auto_round:
        import visual_needs
        filled = visual_needs.fill(course, o.module)
        if filled:
            print("AUTO - %d photo slot(s) filled from the course photo catalogue with no agent (%s) - built again once (%.0f s so far)"
                  % (len(filled), ", ".join("%s <- %s" % x for x in filled), secs))
            sys.stdout.flush()
            return main(list(sys.argv[1:] if argv is None else argv) + ["--auto-round"])
    if passed and slots_left:
        print("PHASE A CLEAN %s - every check that does not depend on the pictures passed: figures, compile + drawing check, words, "
              "navigation, every question graded right and wrong, audits 1280x800 %s, course package (%.0f s)"
              % (m, " ".join(sizes), secs))
        print("  %d picture slot(s) still hold Phase A's stand-ins: %s" % (len(slots_left), ", ".join("%s (%s)" % x for x in slots_left)))
        print("  Phase B: fill them from %s - then build again (only the changed slides are judged) for PASS and the review sheets"
              % needs)
        if stages:
            print(stage_line(stages))
        print("Full log: %s" % log.name)
        return 4
    if passed:
        print("PASS %s - figures, compile + drawing check, words (instructor, trainee), navigation, audits 1280x800 %s, course package"
              " (%.0f s)" % (m, " ".join(sizes), secs))
        try:                                             # 2.67.0 - its drawings, for the next slide that draws the same
            import figure_library
            figure_library.save(course, o.module)
        except Exception:                                # noqa: BLE001 - the library is a help, never a stop
            pass
        gold = cf_timing.clock_pass(course, m)          # 2.65.0 - at the first PASS: its minutes against 30-40
        if gold:
            print(gold)
        if review:
            print(review)
    else:
        print("FAIL %s - %s (%.0f s)" % (m, ", ".join(fails), secs))
        if review and fails == ["course package"]:
            print("MODULE CLEAN - only the course package is left, judged after assembly (compile_course.py, then "
                  "check_course_package.py); the review sheets are promoted:")
            print(review)
    if stages:
        print(stage_line(stages))
    if not o.no_fix:                             # 2.72.7: a check (QA's --no-fix) is no build of the builder's
        done = passed or (o.no_course_pages and fails == ["course package"])        # after the task pages' verdict
        counts = streak(os.path.join(logdir, "%s_streak.json" % m), [] if done else finding_keys(say))
        for x in stop_lines(counts, m):
            print(x)
    print("Full log: %s" % log.name)
    return 0 if passed else 1


ANSWER_WITHIN = 540     # s: a build still running then goes on by itself - under the shell's 10-minute limit (2.63.3)


def running_files(course, module):
    """(the running build's record, its answer file) for this module"""
    import workspace
    import content_script as cs
    logdir = workspace.claude_path(workspace.work_folder(course, create=False), "_build")
    m = cs.mid(module) if str(module).isdigit() else str(module)
    return os.path.join(logdir, "%s_running.json" % m), os.path.join(logdir, "%s_answer.txt" % m), m


def state_key(course, module, args):
    """2.72.3 - everything a build reads and writes, as it is now: the script and build sheet, the module's figures and
    folder (photos, kit_parts.js, what the last build wrote), its review baseline, the factory's own files, the arguments
    and the CF_ settings - by name, size and time, so taking it costs a fraction of a second. Taken when a build ends; the
    same key at the next call means nothing changed since that answer (the 2.66 run's builders built again to re-read a
    report they already had)"""
    import workspace
    import content_script as cs
    import compile_module as cm
    h = hashlib.sha256()
    h.update(json.dumps([sorted(a for a in args if a not in ("--wait", "--inner")),
                         sorted((k, v) for k, v in os.environ.items() if k.startswith("CF_")
                                and k not in ("CF_BUILD_RUNNING", "CF_TIMING", "CF_BUILD_ANSWER_WITHIN", "CF_BUILD_TEST_SLEEP"))]).encode())
    course = workspace.work_folder(course, create=False)
    m = cs.mid(module) if str(module).isdigit() else str(module)
    mdir, _ = cm.module_folder(course, module)
    p = cs.paths(course, module)
    out_dir = workspace.claude_path(course, "review", m)
    files = [p["script"], cm.build_path(course, module)] + [os.path.join(course, x) for x in sorted(os.listdir(course))
                                                              if os.path.isfile(os.path.join(course, x))]
    trees = [workspace_figdir(course, module), mdir or "", out_dir, reviewed_dir(out_dir), os.path.dirname(SKILLS)]
    for f in files:
        try:
            st = os.stat(f)
            h.update(("%s %d %d\n" % (f, st.st_size, st.st_mtime_ns)).encode("utf-8", "replace"))
        except OSError:
            h.update(("%s -\n" % f).encode("utf-8", "replace"))
    for top in trees:
        for root, dirs, names in os.walk(top) if top and os.path.isdir(top) else []:
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", ".git", "node_modules"))
            for n in sorted(names):
                if n.endswith(".pyc"):
                    continue
                try:
                    st = os.stat(os.path.join(root, n))
                except OSError:
                    continue
                h.update(("%s %d %d\n" % (os.path.join(root, n), st.st_size, st.st_mtime_ns)).encode("utf-8", "replace"))
    return h.hexdigest()[:20]


def wait_answer(rec_path, ans_path, m, within):
    """wait for the build in rec_path up to `within` s: (exit code, its answer) when it ended, else None"""
    import browser_slots
    t0 = time.time()
    while True:
        try:
            rec = json.load(io.open(rec_path, encoding="utf-8"))
        except (OSError, ValueError):                    # being written this instant
            rec = None
        done = rec.get("exit") if rec else None
        if rec is not None and (done is not None or not browser_slots.alive(int(rec.get("pid") or 0))):
            try:
                text = io.open(ans_path, encoding="utf-8", errors="replace").read()
            except OSError:
                text = ""
            if done is None:
                return 1, text + "\nFAIL %s - the build ended without its last line (stopped from outside?) - run it again\n" % m
            return int(done), text
        if time.time() - t0 >= within:
            return None
        time.sleep(1)


def entry(argv=None):
    """2.63.3 - the build runs as its own process; this one answers within ANSWER_WITHIN s, with the build's own answer,
    or with STILL BUILDING (exit 3) while the build goes on - the shell call never ends blind. --wait: wait (again) for it.
    The IGF 2.63.2 run: M01's first build took 1,076 s and the builder's 600 s shell call ended without an answer"""
    argv = list(sys.argv[1:] if argv is None else argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--inner" in argv or "--reviewed" in argv or "-h" in argv or "--help" in argv:
        return main(argv)
    slides = any(a == "--slides" or a.startswith("--slides=") for a in argv)     # 2.72.7: seconds, in this process
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    known, _ = ap.parse_known_args(argv)
    try:
        within = float(os.environ.get("CF_BUILD_ANSWER_WITHIN") or ANSWER_WITHIN)
    except ValueError:
        within = ANSWER_WITHIN
    try:
        rec_path, ans_path, m = running_files(known.course, known.module)
    except Exception:                                    # noqa: BLE001 - main says what is wrong with the course
        return main(argv)
    import browser_slots
    try:
        rec = json.load(io.open(rec_path, encoding="utf-8"))
    except (OSError, ValueError):
        rec = {}
    running = rec.get("exit") is None and browser_slots.alive(int(rec.get("pid") or 0))
    if slides:                                   # never beside a running build of the module: it reads the same folder
        if running:
            print("A build of %s is running - check the slides after it answers (the same build command with --wait)" % m)
            return 3
        return main(argv)
    wait = "--wait" in argv
    args = [a for a in argv if a != "--wait"] + ["--inner"]
    if not wait and not running and rec.get("exit") in (0, 1) and rec.get("key") and rec.get("args") == args \
            and not {"--full", "--force"} & set(argv) and os.path.isfile(ans_path):
        try:                                             # 2.72.3: nothing changed since the last answer - that answer
            same = state_key(known.course, known.module, args) == rec["key"]
        except Exception:                                # noqa: BLE001 - not sure: build
            same = False
        if same:
            print("(nothing changed since this build's last answer, %.0f min ago - the same report, nothing built; change a "
                  "file, or --full to build again)" % ((time.time() - rec.get("ended", time.time())) / 60))
            sys.stdout.write(io.open(ans_path, encoding="utf-8", errors="replace").read())
            return int(rec["exit"])
    if wait or running:
        if not rec:
            print("No build of %s to wait for - run build_module.py without --wait" % m)
            return 1
        if running and not wait:
            print("A build of %s is already running (started %.0f s ago) - waiting for it instead of starting another."
                  % (m, time.time() - rec.get("started", time.time())))
    else:
        os.makedirs(os.path.dirname(rec_path), exist_ok=True)
        fh = io.open(ans_path, "w", encoding="utf-8")
        flags = 0
        if os.name == "nt":                          # its own process group, no window; the shell call may end before it
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000      # CREATE_NO_WINDOW
        env = dict(os.environ, PYTHONIOENCODING="utf-8", CF_BUILD_RUNNING=rec_path)
        io.open(rec_path, "w", encoding="utf-8").write(json.dumps({"pid": os.getpid(), "started": time.time(), "args": args}))
        p = subprocess.Popen([PY, os.path.abspath(__file__)] + args, stdout=fh, stderr=subprocess.STDOUT, env=env,
                             creationflags=flags, **({} if os.name == "nt" else {"start_new_session": True}))
        fh.close()
        try:                                         # its PID, keeping an "exit" a very short build may have written already
            rec = json.load(io.open(rec_path, encoding="utf-8"))
        except (OSError, ValueError):
            rec = {"started": time.time(), "args": args}
        rec["pid"] = p.pid
        io.open(rec_path, "w", encoding="utf-8").write(json.dumps(rec))
    got = wait_answer(rec_path, ans_path, m, within)
    if got is None:
        print("STILL BUILDING %s - it goes on by itself (a first build, or a busy computer). Run the same command with --wait: "
              "it waits up to %.0f s more and prints this build's answer. Do not edit the build sheet or the figures meanwhile."
              % (m, within))
        return 3
    code, text = got
    sys.stdout.write(text)
    return code


if __name__ == "__main__":
    if os.environ.get("CF_BUILD_RUNNING") and "--inner" in sys.argv:
        _rec = os.environ["CF_BUILD_RUNNING"]
        try:
            time.sleep(float(os.environ.get("CF_BUILD_TEST_SLEEP") or 0))       # test_build_module.py: a build that takes long
            _code = main()
        except SystemExit as _e:
            _code = _e.code if isinstance(_e.code, int) else 1
        except BaseException:                            # noqa: BLE001 - said in the answer file, then the record
            import traceback
            traceback.print_exc()
            _code = 2
        sys.stdout.flush()
        try:
            _r = json.load(io.open(_rec, encoding="utf-8"))
        except (OSError, ValueError):
            _r = {}
        _r["exit"], _r["ended"] = _code, time.time()
        try:                                             # 2.72.3: the state this answer belongs to (entry() reuses it)
            _a = argparse.ArgumentParser(add_help=False)
            _a.add_argument("course")
            _a.add_argument("--module", required=True)
            _k, _ = _a.parse_known_args(sys.argv[1:])
            _r["key"] = state_key(_k.course, _k.module, sys.argv[1:])
        except Exception:                                # noqa: BLE001 - no key: the next call builds
            pass
        io.open(_rec, "w", encoding="utf-8").write(json.dumps(_r))
        sys.exit(_code)
    sys.exit(entry())
