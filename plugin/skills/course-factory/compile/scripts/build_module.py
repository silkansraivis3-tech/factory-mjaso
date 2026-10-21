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
Exit 0 PASS, 1 problems to fix, 2 stopped (the compiler refused: not approved, changed by hand, design files edited).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
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


def run(cmd, timeout=900):
    """(exit code, output) of one tool, run as its own process (as the person would run it)"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 2, "timed out after %d s: %s" % (timeout, " ".join(cmd))
    except OSError as err:
        return 2, "could not run %s: %s" % (cmd[0], err)


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
    out = []
    if pics:
        out.append((pics, "its picture: \"figure\" - a photo in assets\\img, a drawing, or a kit spec"))
    if ons:
        out.append((ons, "the drawing or photo the question is answered on: \"figure\" (and its places, \"areas\" / \"labels\")"))
    if scenes:
        out.append((scenes, "the planned 3D scene is not written - build it, or keep the 2D starter (\"_2d\") with the operator's "
                            "reason in \"declined_3d\""))
    return out


def write_stages(log, stages, t0):
    """2.52.0 - each stage's seconds at the end of the build log: which stage a slow build spent its time in (M01/M02
    workflow benchmark: build runs of 100-400 s, and no way to tell the figures from the audits from the review sheets)"""
    log.write("\n===== stage seconds\n%s\n%-52s %6.0f s\n" % ("\n".join("%-52s %6.0f s" % (k, v) for k, v in stages),
                                                            "total", time.time() - t0))


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
    blanks = [] if o.draft else starter_blanks(course, o.module)
    if blanks:                       # 2.52.0: nothing is built on a sheet with the starter's blanks in it
        print("FAIL %s - nothing built: the build sheet %s still has the starter's blanks - fill %s"
              % (m, os.path.basename(cm.build_path(course, o.module)),
                 "; ".join("%s: %s" % (", ".join(ids), what) for ids, what in blanks)))
        return 1
    log = io.open(os.path.join(logdir, "%s_build.log" % m), "w", encoding="utf-8")
    say, fails, notes = [], [], []
    stages = []                      # 2.52.0: (stage, seconds) - written into the log, so a slow stage is seen

    def logged(title, out):
        log.write("\n===== %s\n%s\n" % (title, out))

    def timed(title, since):
        stages.append((title, time.time() - since))
        return time.time()

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
            say += body
        if fcode:
            fails.append("figures")
    t = timed("figures (figure_fit.py)", t0)
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
                                                                r"photo over drawing|scrolls)\b", x) for x in probs)
    shown = figure_slides(fig_text)
    probs = [x for x in probs if not any(re.search(r"\(%s\)[ :]" % re.escape(s), x) and re.search(r"\b(empty|text zone|inside|"
                                                                                                    r"cut off|small text|label|contrast)\b", x)
                                         for s in shown)]
    if ccode != 0 or probs:
        fails.append("compile")
        say.append("COMPILE - %d problem(s) to fix%s:" % (len(probs), " (the figures above not repeated)" if shown else ""))
        say += ["  - " + x for x in probs]
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
    out_dir = workspace.claude_path(course, "review", m)
    pending = out_dir + ".pending"
    want_review = not o.no_review and not fails
    if want_review:
        import shutil
        shutil.rmtree(pending, ignore_errors=True)
        jobs["review sheets"] = ["node", os.path.join(MEASURE, "review_sheets.mjs"), mdir, pending, "--base=" + out_dir]
    results, took = {}, {}

    def run_timed(k, c):
        s = time.time()
        r = run(c)
        took[k] = time.time() - s
        return r
    pkg_cmd = [PY, os.path.join(FACTORY, "check_course_package.py"), os.path.join(course, workspace.MODULES)]
    with cf.ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(run_timed, k, c): k for k, c in jobs.items()}
        pkg = None
        for f in cf.as_completed(futs):
            results[futs[f]] = f.result()
            # the importer reads every file of the module folder: it waits for the audits, whose probe pages come and go
            # in presentation\, and for the course pages; it then runs beside the review sheets
            if pkg is None and all(k in results for k in jobs if k != "review sheets"):
                pkg = ex.submit(run_timed, "course package", pkg_cmd)
        if pkg is None:
            pkg = ex.submit(run_timed, "course package", pkg_cmd)
        results["course package"] = pkg.result()
    t = timed("the checks, at the same time (wall clock)", t)
    stages += [("  " + k, took[k]) for k in list(jobs) + ["course package"] if k in took]
    if o.no_course_pages:
        pcode, pout, left = own_package_findings(*results["course package"], folder=os.path.basename(mdir))
        if left and pcode != 0:
            # the module's own findings fail it; the left-out ones are only listed in the log
            pout += "\n(%d of the findings above concern the course's own pages or another module - the check after assembly's)\n" % left
        results["course package"] = (pcode, pout)
        if left:
            notes.append("Course package: %d finding(s) about the course's own pages or other modules left to the check after "
                         "assembly (compile_course.py, then check_course_package.py)" % left)
    for k in [x for x in jobs if x != "review sheets"] + ["course package"]:
        code, out = results[k]
        logged(k, out)
        if code != 0:
            fails.append(k)
            say.append("%s - FAIL:" % k.upper())
            # the audits name every element and its words (run_audits.summarise), so they keep more lines - no --json run to find them
            say += ["  " + x for x in lines_of("\n".join(y for y in out.splitlines() if not y.startswith("Built ")),
                                               40 if k.startswith("audits") else 12)]
    passed = not fails
    review = ""
    if want_review and passed:
        rcode, rout = results["review sheets"]
        if rcode == 0:                          # the sheets are the review now: the last review's folder is replaced
            import shutil
            shutil.rmtree(out_dir, ignore_errors=True)
            os.replace(pending, out_dir)
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
                       "  Give the sheets to ONE review subagent (model haiku or sonnet) with %s - it returns a short verdict."
                       % (n.group(1), n.group(2), n.group(3), out_dir, os.path.join(SKILLS, "course-factory", "compile", "REVIEW_PROMPT.md")))
                      if n and n.group(1) != "0" else
                      "Visual review: no screen changed since the last review - nothing new to look at.")
        else:
            notes.append("Review sheets not made (%s) - do the visual review by hand (GUIDE 2f)" % (lines_of(rout, 1) or ["?"])[0])
    write_stages(log, stages, t0)
    log.close()
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
    print("Full log: %s" % log.name)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
