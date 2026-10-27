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
    2.65.0, at most 45 min; --long-pole goes first): wave 1's three first builds overlapped and M01's took 1,076 s;
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
3 still building (run the same command with --wait).
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
        fig = (e.get("figure") or "").strip()
        if s["kind"] == "slide" and not s.get("recap") and not fig and (s.get("visual_kind") or "none") != "none":
            pics.append(s["id"])
        elif s["kind"] in cs.TASKS and cs.mech(s) in cm.STARTER_ON_PICTURE and not fig:
            ons.append(s["id"])
        elif s["kind"] == "slide" and re.fullmatch(r"m\w+_%s_3d\.html" % re.escape(s["id"]), fig) \
                and not (build.get("declined_3d") or e.get("declined_3d")) \
                and not any(os.path.isfile(os.path.join(d, fig)) for d in (figdir, mdir) if d):
            scenes.append(s["id"] + " (" + fig + ")")
        elif s["kind"] == "slide" and fig.lower().endswith(".kit3d.json") and not (build.get("declined_3d") or e.get("declined_3d")):
            # 2.65.0 - a 3D-kit scene: missing, or still --init-build's starter ("_todo": parts guessed, not placed)
            p = os.path.join(figdir, fig)
            try:
                todo = bool(json.load(io.open(p, encoding="utf-8")).get("_todo"))
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


# 2.66.5 - THE LAYOUT PRE-CHECK. WHY (Desktop\IGF_course_2.66_figures\SPEED_ANALYSIS.md): a slide the compiler built
# another way for L62 that did not fit was found only by the deck audit at the END of a build, and the whole module was
# built again (a LAYOUT round: the figures - a moved slide's figure measured and re-fitted in its new column - the
# compile and every check) - 23.5 of IGF M03's 39.5 build-minutes in the 2.66.3 run, 30 of M02's in the 2.66 run 2,
# where s02 / s14 went through it in four builds running. Now, before the figures, the deck is laid out in memory
# (compile_deck, as figure_fit does) and ONLY the slides built another way that the last build did not build so are
# audited, by run_audits.py's own probes at the build's sizes, the whole deck loaded (run_audits --only's way); a misfit
# is measured out at once (MNN_layout_avoid.json, as before) and the deck laid out again, at most LAYOUT_ROUNDS times.
# The audit at the end still judges every slide, and still builds again if one does not fit after all (a figure fitted
# in the build can change its panel). CF_LAYOUT_PRECHECK=off: not run.
def varied_new(deck_html, last, seen=()):
    """{sid: slide index from 0} - the slides built another way for L62 (data-varied) that the last build did not build
    that way (MNN_layouts.json: the same words and the same look), and not checked already (seen: (sid, shape, ground))"""
    out = {}
    for k, (sid, shape, ground, words) in varied_slides(deck_html):
        a = (last or {}).get(sid) or {}
        kept = a.get("words") == words and list(a.get("key") or []) == [shape, ground]
        if not kept and (sid, shape, ground) not in seen:
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


def layout_precheck(course, module, mdir, logdir, m, sizes, audit=None):
    """-> ([log lines], {sid: (shape, ground)} measured out). audit(deck path, size, [slide index]) -> (result, error):
    run_audits.measure by default (the test passes its own)"""
    import workspace
    import content_script as cs
    import compile_module as cm
    if MEASURE not in sys.path:
        sys.path.insert(0, MEASURE)
    import run_audits as ra
    from pathlib import Path
    mid_ = cs.mid(module)
    work = workspace.claude_path(course)
    p = cs.paths(course, module)
    script, build = cs.load(p["script"]), cs.load(os.path.join(p["dir"], mid_ + ".build.json"))
    figdir = os.path.join(os.path.dirname(p["dir"]), "figures", mid_)
    last = cm.load_layouts(work, mid_)
    lines, out, seen = [], {}, set()
    if audit is None:
        exe, offset = ra.browser(), []
        if not exe:
            return ["no Chrome or Edge - not checked (the audit at the end judges every slide)"], {}

        def audit(deck, size, only):
            if not offset:
                offset.append(ra.frame_offset(exe))
            return ra.measure(exe, Path(deck), size, 240000, offset[0], only)     # run_audits.py's own budget
    for rnd in range(LAYOUT_ROUNDS + 1):
        deck, _, _ = cm.compile_deck(script, build, mdir, figdir, "CACHE", True, cm.load_layout_avoid(work, mid_), last, {})
        todo = varied_new(deck, last, seen)
        if not todo:
            break
        page = os.path.join(mdir, "presentation", "_layout_precheck_%d.html" % os.getpid())
        io.open(page, "w", encoding="utf-8", newline="\n").write(deck)
        try:
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=len(sizes)) as ex:
                got = list(ex.map(lambda s: audit(page, s, sorted(todo.values())), sizes))
        finally:
            try:
                os.remove(page)
            except OSError:
                pass
        text = []
        for res, err in got:
            if res is None:
                lines.append("not measured (%s) - the audit at the end judges every slide" % err)
                return lines, out
            for name, _, _ in ra.PROBES:
                text += ra.summarise(name, res.get(name) or {"ABORTED": "no result"})[2]
        mis = {k: v for k, v in moved_misfits(deck, "\n".join(text)).items() if k in todo}
        seen |= {(sid, shape, ground) for _, (sid, shape, ground, _) in varied_slides(deck) if sid in todo}
        lines.append("round %d: %d slide(s) built another way checked (%s)%s" % (
            rnd + 1, len(todo), ", ".join(sorted(todo)), "; did not fit: " + ", ".join(
                "%s (%s, %s ground)" % (k, v[0], v[1]) for k, v in sorted(mis.items())) if mis else " - every one fits"))
        if not mis:
            break
        measure_out(os.path.join(logdir, "%s_layout_avoid.json" % m), mis)
        out.update({k: v[:2] for k, v in mis.items()})
    return lines, out


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


# ------------------------------------------------------------------ 2.65.0: the short answer
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
            elif line.startswith("    tried by itself:") and "APPLIED to " in line:      # 2.66.3: the build did it
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
    ap.add_argument("--viewport", action="append", default=[], help="another audit size, WxH (1280x800 and 1024x768 always run)")
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
    ap.add_argument("--long-pole", action="store_true", help="the course's biggest module (build_order.py, 2.65.0): its first "
                                                             "build never waits for another module's first build")
    ap.add_argument("--full-output", action="store_true", help="print every finding in full, as the log has it (2.65.0: the "
                                                               "answer is one line per problem, with its fix)")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
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
    out_dir = workspace.claude_path(course, "review", m)
    if o.reviewed:
        return mark_reviewed(out_dir, m)
    blanks = [] if o.draft else starter_blanks(course, o.module)
    if blanks:                       # 2.52.0: nothing is built on a sheet with the starter's blanks in it
        print("FAIL %s - nothing built: the build sheet %s still has the starter's blanks - fill %s"
              % (m, os.path.basename(cm.build_path(course, o.module)),
                 "; ".join("%s: %s" % (", ".join(ids), what) for ids, what in blanks)))
        return 1
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
    say, fails, notes = [], [], []
    stages = []                      # 2.52.0: (stage, seconds) - written into the log, so a slow stage is seen

    def logged(title, out):
        log.write("\n===== %s\n%s\n" % (title, out))

    def timed(title, since):
        stages.append((title, time.time() - since))
        return time.time()

    # 2.66.5 - the slides built another way for L62 are audited before anything is built (layout_precheck); its seconds
    # are a stage of their own, the figures' clock starts after it
    t_fig = t0
    if o.layout_round == 0 and not o.draft and str(o.module).isdigit() and os.path.isdir(os.path.join(mdir, "presentation")) \
            and (os.environ.get("CF_LAYOUT_PRECHECK") or "").lower() not in ("off", "0", "no"):
        try:
            pre_lines, pre_out = layout_precheck(course, o.module, mdir, logdir, m,
                                                 [(1280, 800), (1024, 768)] + [tuple(int(x) for x in v.split("x")) for v in o.viewport
                                                                              if v not in ("1280x800", "1024x768")])
        except Exception as err:                     # noqa: BLE001 - the audit at the end still judges every slide
            pre_lines, pre_out = ["could not run (%s) - the audit at the end judges every slide" % err], {}
        logged("layout pre-check (L62)", "\n".join(pre_lines) or "no slide built another way that the last build did not build so")
        t_fig = timed("layout pre-check (L62)", t0)
        if pre_out:
            notes.append("LAYOUT (pre-check) - %d slide(s) built another way so no two neighbours look alike (L62) did not "
                         "fit and are built their next way: %s (kept in %s_layout_avoid.json while their words are unchanged)"
                         % (len(pre_out), ", ".join("%s (%s, %s ground)" % (k, v[0], v[1]) for k, v in sorted(pre_out.items())), m))
    # 2.63.3 - a module's first build (never built here: no _last.json) measures every figure and tries every fix: one at a
    # time on the computer, the others wait their turn (a queue, 2.65.0) - held through the figures and the compile
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
        notes.append("Real photographs still to take: %d thing(s), listed in %s" % (len(mm.group(2).strip().splitlines()), mm.group(1).strip()))
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
    sizes = ["1024x768"] + [v for v in o.viewport if v not in ("1280x800", "1024x768")]
    if os.path.isfile(deck):
        # 2.57.0 - a slide audited clean and unchanged in everything it loads is not measured again (--full: every slide)
        a = [PY, os.path.join(MEASURE, "run_audits.py"), deck, "--quiet", "--cache", os.path.join(logdir, "%s_audits_clean.json" % m)]
        a += ["--full"] if o.full else []
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
                                 "--shots=" + os.path.join(logdir, "%s_shots" % m)]
    pkg_cmd = [PY, os.path.join(FACTORY, "check_course_package.py"), os.path.join(course, workspace.MODULES)]
    ak = next((k for k in jobs if k.startswith("audits")), None)

    def will_retry(k, res):
        """the audits failed a slide the compiler built another way for L62: this round is built again (2.62.0)"""
        if k != ak or res[0] == 0 or o.layout_round >= LAYOUT_ROUNDS or not os.path.isfile(deck):
            return None
        return moved_misfits(io.open(deck, encoding="utf-8").read(), res[1])
    results, took, early = run_checks(jobs, pkg_cmd, will_retry)
    t = timed("the checks, at the same time (wall clock)", t)
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
            if k.startswith("audits") and not o.full_output:      # 2.65.0: per slide, each kind once with its count
                say += short_audits(out)
            else:
                say += ["  " + x for x in lines_of("\n".join(y for y in out.splitlines() if not y.startswith("Built ")),
                                                   40 if k.startswith("audits") else 12)]
    # 2.62.0 - a slide the compiler built another way for L62 that the audit found does not fit is measured out and built
    # its next way, at once: the builder never pins a layout by hand for what the compiler chose
    if ak in fails and o.layout_round < LAYOUT_ROUNDS and os.path.isfile(deck):
        mis = early or moved_misfits(io.open(deck, encoding="utf-8").read(), results[ak][1])
        if mis:
            measure_out(os.path.join(logdir, "%s_layout_avoid.json" % m), mis)
            log.write("\n===== this round's findings (the build runs again for the slides above)\n%s\n" % "\n".join(say))
            write_stages(log, stages, t0, timing)
            log.close()
            os.replace(log.name, os.path.join(logdir, "%s_build.round%d.log" % (m, o.layout_round + 1)))
            print("LAYOUT - %d slide(s) built another way so no two neighbours look alike (L62) did not fit: %s - built again "
                  "their next way (%.0f s; kept in %s_layout_avoid.json while their words are unchanged)"
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
        if rcode == 0:                          # the sheets are the review now: the last review's folder is replaced
            promote(pending, out_dir)
            rout = rout.replace(pending, out_dir)
        logged("review_sheets.mjs", rout)
        if rcode == 1:                          # not promoted: the next review still compares with the last one shown
            passed = False
            fails.append("task pages")
            say.append("TASK PAGES - FAIL (review_sheets.mjs answered every question by its own keys and checked every leader "
                       "line as the engine placed it - fix the drawing or the build sheet's \"labels\"):")
            say += ["  " + x for x in rout.splitlines() if "FAIL" in x]
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
    if passed:
        print("PASS %s - figures, compile + drawing check, words (instructor, trainee), navigation, audits 1280x800 %s, course package"
              " (%.0f s)" % (m, " ".join(sizes), secs))
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
    """2.66.3 - everything a build reads and writes, as it is now: the script and build sheet, the module's figures and
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
    wait = "--wait" in argv
    args = [a for a in argv if a != "--wait"] + ["--inner"]
    if not wait and not running and rec.get("exit") in (0, 1) and rec.get("key") and rec.get("args") == args \
            and not {"--full", "--force"} & set(argv) and os.path.isfile(ans_path):
        try:                                             # 2.66.3: nothing changed since the last answer - that answer
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
        try:                                             # 2.66.3: the state this answer belongs to (entry() reuses it)
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
