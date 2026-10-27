# -*- coding: utf-8 -*-
"""test_build_module - build_module.py's course-package verdict in a parallel build (2.51.0).

    python test_build_module.py

With --no-course-pages a module agent never writes COURSE.html or any START_HERE page - compile_course.py does, once
every module is in. Before 2.51.0 the package check still failed on those missing pages (and on the other modules'),
so no module of a parallel build could PASS and none reached its review sheets (benchmark 2026-10-20, workflow_before).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import build_module as b  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


# check_course_package.py's own words, from the benchmark course before assembly (shortened)
OUT = """Course folder: C:\\c\\modules
  16 module(s)

6 thing(s) to fix before it goes into the classroom:
  - module01/START_HERE.html is missing - opens the presentation (L43)
  - module01/presentation/index.html uses ../START_HERE_EXTENDED.html, which is not there
  - module02/START_HERE_EXTENDED.html is missing - the instructor's quick-access page (L43)
  - module02/tasks/sc1_a.html has no <title>
  - the classroom's importer: Link outside the package: instructor/COURSE.html → instructor/module01/START_HERE.html
  - _course_shell/course_map.js lists M01, the folder has module01, module02

Worth a look (does not stop it):
  - module01: 11 drawn subjects still need a real photograph
"""


def main():
    code, out, left = b.own_package_findings(1, OUT, "module01")
    check("module 1 of a parallel build: the missing course pages and module 2's own problem do not fail it",
          code == 0 and left == 6 and "none (6 left to the check after assembly)" in out, (code, left, out))
    check("... and the notes the check printed are kept", "real photograph" in out, out)
    code, out, left = b.own_package_findings(1, OUT, "module02")
    check("module 2: its own problem (a task page with no <title>) still fails it",
          code == 1 and left == 5 and "sc1_a.html has no <title>" in out, (code, left))
    pre = OUT.replace("6 thing(s)", "9 thing(s)").replace(
        "  - _course_shell/course_map.js",
        "  - the classroom's importer: The course ID must be a unique name without spaces.\n"
        "  - the classroom's importer: Give the course title.\n"
        "  - .tmp.drivedownload\\ is not a module (module01 ...) - the factory's own material belongs in working_claude\n"
        "  - _course_shell/course_map.js")
    code, out, left = b.own_package_findings(1, pre, "module01")
    check("2.58.0 before assembly: the importer's missing course ID / title and a sync tool's folder are not module 1's "
          "(the IGF full build: no module ever saw PASS)", code == 0 and left == 9, (code, left, out))
    mine = OUT.replace("  - module02/tasks/sc1_a.html has no <title>", "  - module01/presentation/index.html has no data-title")
    check("a module's own finding beside the course-page ones fails it",
          b.own_package_findings(1, mine, "module01")[0] == 1)
    check("a passing package and a stop (exit 2) are passed through untouched",
          b.own_package_findings(0, "Ready", "module01") == (0, "Ready", 0)
          and b.own_package_findings(2, "Stopped", "module01") == (2, "Stopped", 0))
    last = {"inputs": "k1", "only_figures": True}
    check("2.56.0 a figures-only round: only figures fail, the last full build failed on figures alone, same inputs -> stop",
          b.figures_only_round(["figures"], False, last, "k1"))
    check("... never when the script or build sheet changed, the last build failed on more, --full, or nothing failed yet",
          not b.figures_only_round(["figures"], False, last, "k2")
          and not b.figures_only_round(["figures"], False, {"inputs": "k1", "only_figures": False}, "k1")
          and not b.figures_only_round(["figures"], True, last, "k1")
          and not b.figures_only_round([], False, last, "k1")
          and not b.figures_only_round(["figures"], False, {}, "k1"))
    blanks_part()
    stages_part()
    layout_part()
    precheck_part()
    solver_part()
    retry_part()
    review_part()
    long_part()
    short_part()
    streak_part()
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


def blanks_part():
    """2.52.0 - a build sheet with --init-build's blanks still in it builds nothing; one line says what to fill (M01 workflow
    benchmark run 1: a 68 s build whose eight compile problems were all blanks)"""
    import io
    import json
    import shutil
    import subprocess
    import tempfile
    import test_compile_module as tcm
    import content_script as cs
    tmp = tempfile.mkdtemp(prefix="bm_blanks_")
    try:
        sc = tcm.script(screens=tcm.SCREENS + [
            {"id": "q02", "kind": "self-check", "set": "SC1", "mechanic": "hotspot", "question": "Tap the vent mast.",
             "visual": "the ship", "answer": "Vent mast*\nFuel tank", "feedback": "High above the deck."}])
        c, md = tcm.new_course(tmp, sc)
        check("a filled build sheet has no blanks", b.starter_blanks(c, 1) == [], b.starter_blanks(c, 1))
        tcm.build_of(c, lambda s: s["screens"].update(s01={"figure": "", "visual_kind": "photo"}, q02={"figure": "", "areas": {}},
                                                       s04={"figure": "m01_s04_3d.html", "visual_kind": "model_3d"}))
        got = b.starter_blanks(c, 1)
        check("the starter's blanks are found: a slide with no picture, a question on no picture, a planned 3D scene not written",
              [x[0] for x in got] == [["s01"], ["q02"], ["s04 (m01_s04_3d.html)"]], got)
        p = subprocess.run([sys.executable, os.path.join(HERE, "build_module.py"), c, "--module", "1"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=300)
        out = (p.stdout or "") + (p.stderr or "")
        check("build_module.py builds nothing on it (exit 1) and says in one line what to fill",
              p.returncode == 1 and out.strip().count("\n") == 0 and out.startswith("FAIL M01 - nothing built")
              and "s01" in out and "q02" in out and "declined_3d" in out
              and not os.path.isfile(os.path.join(md, "presentation", "index.html")), (p.returncode, out))
        # 2.72.3 - the same build again, nothing changed since its answer: that answer at once, nothing built
        import time
        env = dict(os.environ, CF_BUILD_TEST_SLEEP="6", CF_BUILD_ANSWER_WITHIN="60")
        again = lambda *extra: subprocess.run([sys.executable, os.path.join(HERE, "build_module.py"), c, "--module", "1"] + list(extra),
                                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, env=env)
        t = time.time()
        p2 = again()
        t2 = time.time() - t
        check("2.72.3 nothing changed since the last answer: the same report and exit code at once (%.1f s), said so" % t2,
              p2.returncode == 1 and t2 < 5 and p.stdout.strip() in p2.stdout and "nothing changed since" in p2.stdout,
              (p2.returncode, t2, p2.stdout))
        t = time.time()
        p3 = again("--full")
        check("... --full builds again", time.time() - t >= 6 and p3.returncode == 1, (p3.returncode, p3.stdout))
        tcm.build_of(c, lambda s: s["screens"]["s01"].update(caption="changed"))
        t = time.time()
        p4 = again()
        check("... and so does a changed build sheet", time.time() - t >= 6 and "nothing changed" not in p4.stdout,
              (p4.returncode, p4.stdout))
        tcm.build_of(c, lambda s: s["screens"]["s04"].update(declined_3d="the operator keeps the flat drawing"))
        check("a 3D scene declined with the operator's reason is no blank", [x[0] for x in b.starter_blanks(c, 1)] == [["s01"], ["q02"]],
              b.starter_blanks(c, 1))
        # 2.71.0 - a 3D-kit scene still --init-build's starter ("_todo") is a blank too; placed (no "_todo"), it is not
        figdir = b.workspace_figdir(c, 1)
        os.makedirs(figdir, exist_ok=True)
        io.open(os.path.join(figdir, "s04.kit3d.json"), "w", encoding="utf-8").write(json.dumps({"_todo": "place the parts", "parts": []}))
        tcm.build_of(c, lambda s: s["screens"]["s04"].update(figure="s04.kit3d.json", declined_3d=None))
        check("2.71.0 a 3D-kit scene still the starter (\"_todo\") is a blank", ["s04 (s04.kit3d.json)"] in [x[0] for x in b.starter_blanks(c, 1)],
              b.starter_blanks(c, 1))
        io.open(os.path.join(figdir, "s04.kit3d.json"), "w", encoding="utf-8").write(json.dumps({"parts": [{"id": "T", "type": "tank_c"}]}))
        check("... placed, it is not", ["s04 (s04.kit3d.json)"] not in [x[0] for x in b.starter_blanks(c, 1)], b.starter_blanks(c, 1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# a 2.63.3 build's figure report and audit answer, as figure_fit.py and run_audits.py printed them (IGF M02, shortened)
FIG = """  s02 (s02.kit.json) on its slide - drawn 456x277 px in a 480x301 px panel, scale 0.63:
    label - Natural gas: detailed rules: found no clear place - give the figure more room (its size, a part moved), or shorten the  (step -)
    small text - Ammonia-33°C: drawn at 9.7 px - the floor is 12.5 px (step 0)
    small text - CNG compressed: drawn at 9.7 px - the floor is 12.5 px (step 0)
    small text - LNG -162°C: drawn at 9.7 px - the floor is 12.5 px (step 0)
    text zone - CNG compressed: two labels print over each other - text.kit-cap "Natural gas" (step 7)
    fix (label): a label found no clear place: give the figure more room around that part, or shorter words
    fix (small text): too many words for the room the figure has: give it a wider column or fewer words
    fix (text zone): give the part room for its words (a larger w/h, or move it clear) - the label layout places words, not parts
    tried by itself: re-fitted to its 480 px column: 4 finding(s) left (was 5) - saved as C:\\c\\figures\\M02\\_fit\\s02.s02.candidate.kit.json: copy it over s02.kit.json and fix what it leaves:
        small text - LNG: drawn at 11 px (step 0)
    the parts named, as the spec has them - change them together: T tree x 10 y 50 w 540
    try a fix in seconds, every step at once: course-visuals\\kit\\scripts\\studio.py s02.kit.json --step all (then one build_module.py run)
    (unchanged since the last build - its report is repeated, not measured again; change the spec or the slide, or build_module.py --full)
  s05 (s05.kit.json): fixed by itself - COLUMN: re-fitted to its 480 x 301 px column - drawn 422 units wide (was 640), 2 round(s)
  (the compile's drawing check judges) q05 (q05.kit.json, task page): empty - blank 44 % of the frame"""
AUD = """1280x800  deck     FAIL n=2   20 slides
            slide 5 (s05): scrolls div.slide-body by 21 px
1024x768  deck     FAIL n=6   20 slides
            slide 2 (s02): drawing text too small "IGF Code" 11.4 px on screen
            slide 2 (s02): drawing text too small "LNG-162°C" 9.5 px on screen
            slide 2 (s02): drawing text too small 10.2 px on screen
            slide 2 (s02): scrolls div.slide-body by 64 px
            slide 3 (s03): drawing text too small "Fuel tank" 11.2 px on screen"""


def short_part():
    """2.71.0 - the build's answer says each problem once, with its fix and its file; the full log keeps every line"""
    print("-- 2.71.0 the short answer: one line per figure and kind of problem, with its fix; audits per slide and kind")
    s = b.short_figures(FIG.splitlines(), r"C:\c\figures\M02")
    text = "\n".join(s)
    check("a figure is one header with its spec's path, its scale and panel, and each kind of problem counted",
          s[0].startswith("  FIGURE s02 - C:\\c\\figures\\M02\\s02.kit.json (scale 0.63 in a 480x301 px panel): ")
          and "small text x3" in s[0] and "label x1" in s[0] and "text zone x1" in s[0] and "unchanged since the last build" in s[0], s[:2])
    check("... each kind once, with an example and its one fix (not one line per part and step)",
          sum(1 for x in s if x.startswith("    small text - e.g.")) == 1 and "fix: fewer / shorter words" in text
          and "Ammonia-33°C" in text and "LNG -162°C" not in text, text)
    check("... the saved closer fit, the parts named and the studio command kept; the long hints and the candidate's list not",
          "a closer fit was saved: C:\\c\\figures\\M02\\_fit\\s02.s02.candidate.kit.json" in text and "T tree x 10 y 50 w 540" in text
          and "studio.py C:\\c\\figures\\M02\\s02.kit.json --quick (then one --step all to look)" in text and "fix (label):" not in text
          and "LNG: drawn at 11 px" not in text, text)
    check("... a figure fixed by itself, and a task page's line, pass through as they are",
          any(x.startswith("  s05 (s05.kit.json): fixed by itself") for x in s) and any("q05 (q05.kit.json, task page)" in x for x in s), s)
    check("... and it is shorter than the report it replaces", len(text) < 0.8 * len(FIG), (len(text), len(FIG)))
    check("the same compile line twice is one line with its count",
          b.short_list(["slide 5 (s05): cut off - circle", "slide 5 (s05): cut off - circle", "slide 5 (s05): scrolls"])
          == ["slide 5 (s05): cut off - circle (x2)", "slide 5 (s05): scrolls"])
    a = b.short_audits(AUD)
    check("audits: per viewport and slide, each kind once with its count and the range of px",
          "  1024x768 slide 2 (s02): drawing text too small x3 (9.5-11.4 px)" in a and "  1280x800 slide 5 (s05): scrolls div.slide-body by 21 px" in a
          and "  1024x768 slide 2 (s02): scrolls div.slide-body by 64 px" in a
          and any(x.startswith("  1024x768 slide 3 (s03): drawing text too small") for x in a), a)
    named = lambda t: {(m, k) for m in ("s02", "s03", "s05") for k in ("too small", "scrolls") if any(m in x and k in x for x in t.splitlines())}
    check("... every slide and kind the audits named is still named", named(AUD) == named("\n".join(a)), (named(AUD), a))


def streak_part():
    """2.72.7 - the stop rule: the same finding three builds running (the 2.72.5 run: M02 s05 over-filled in all 20 builds)"""
    import io
    import json
    import tempfile
    print("-- 2.72.7 the stop rule: the same finding three builds running")
    say = ["FIGURES"] + b.short_figures(FIG.splitlines(), r"C:\c\figures\M02") + ["AUDITS 1280x800 1024x768 - FAIL:"] + b.short_audits(AUD)
    keys = b.finding_keys(say)
    check("each top-level finding is a key, a figure one per kind of problem; a figure fixed by itself is none",
          "FIGURE s02: small text" in keys and "FIGURE s02: label" in keys and not any("s05 (s05.kit.json)" in k for k in keys)
          and "#x# slide # (s05): scrolls div.slide-body by # px" in keys, keys)
    moved = [x.replace("21 px", "34 px").replace("64 px", "12 px").replace("x3 (9.5-11.4 px)", "x2 (11.9-12.2 px)")
             .replace("scale 0.63", "scale 0.71").replace("small text x3", "small text x1") for x in say]
    check("... the same while only its numbers move (px, counts, the figure's scale)", b.finding_keys(moved) == keys,
          (b.finding_keys(moved), keys))
    path = os.path.join(tempfile.mkdtemp(prefix="bm_streak_"), "M02_streak.json")
    got = [b.stop_lines(b.streak(path, keys), "M02") for _ in range(2)]
    check("two builds running: nothing said", got == [[], []], got)
    third = b.stop_lines(b.streak(path, b.finding_keys(moved)), "M02")
    check("the third: SAME FINDING 3 BUILDS RUNNING names them, and STOP - everything left is such a finding",
          len(third) == 2 and third[0].startswith("SAME FINDING 3 BUILDS RUNNING") and "FIGURE s02: small text" in third[0]
          and third[1].startswith("STOP - everything this build prints has failed 3 builds running"), third)
    new = keys + ["COMPILE line: - Slide 9 (s09) looks exactly like the slide before it (L62)"]
    fourth = b.stop_lines(b.streak(path, new), "M02")
    check("... a new finding beside them: they are still named, but no STOP (there is work the build can still show)",
          len(fourth) == 1 and fourth[0].startswith("SAME FINDING") and "s09" not in fourth[0], fourth)
    b.streak(path, [k for k in keys if "s02" not in k])
    after = json.load(io.open(path, encoding="utf-8"))
    check("a finding a build does not print starts again; a clean build starts every count again",
          not any("s02" in k for k in after) and b.streak(path, []) == {} and b.stop_lines({}, "M02") == [], after)
    src = io.open(os.path.join(HERE, "build_module.py"), encoding="utf-8").read()
    check("build_module.py says it on every builder's answer (the figures-only round too), never on QA's --no-fix check",
          src.count("stop_lines(") >= 3 and src.count("# 2.72.7: a check (QA's --no-fix) is no build of the builder's") == 2, "")


def stages_part():
    import io
    import time
    buf = io.StringIO()
    b.write_stages(buf, [("figures (figure_fit.py)", 41.2), ("compile (compile_module.py, its drawing check)", 63.0),
                         ("  audits 1280x800 1024x768", 120.4)], time.time() - 230)
    text = buf.getvalue()
    check("2.52.0: the build log ends with each stage's seconds and the total",
          "===== stage seconds" in text and "figures (figure_fit.py)" in text and "41 s" in text and "120 s" in text
          and "total" in text and "230 s" in text, text)
    # 2.63.2 (the M01 benchmark's METRICS: a FAIL build gave only its total) - the stages on the build's own answer too
    line = b.stage_line([("figures (figure_fit.py)", 41.2), ("compile (compile_module.py, its drawing check)", 63.0)])
    check("2.63.2: the answer names each stage's seconds - 'Stages: figures 41 s · compile 63 s'",
          line == "Stages: figures 41 s · compile 63 s", line)
    src = io.open(os.path.join(HERE, "build_module.py"), encoding="utf-8").read()
    tail = src[src.index('print("FAIL %s - %s (%.0f s)"'):]
    check("... printed after a FAIL as after a PASS, and after a figures-only FAIL",
          "print(stage_line(stages))" in tail[:600] and src.count("print(stage_line(stages))") >= 2, tail[:600])


def layout_part():
    """2.62.0 - a slide the compiler built another way for L62 that the audit failed is measured out (IGF M04 s05: 102
    words under a photograph across the slide spilled 66 px; no word count would have told)"""
    import io
    import json
    import tempfile
    deck = ('<section class="slide" data-script="s04" data-template="explain-figure.v1">\n'
            '<section class="slide" id="s05" data-script="s05" data-varied="picture-top|light|a1b2c3d4e5f6">\n'
            '<section class="slide dark" data-script="s06" data-varied="picture-left|dark|0123456789ab">')
    audit = ("  1024x768  deck     FAIL n=3   13 slides\n              slide 5 (s05): spills ul.support by 66 px\n"
             "              slide 4 (s04): spills div.copy by 7 px\n")
    got = b.moved_misfits(deck, audit)
    check("only a failing slide the compiler moved is a misfit - not one built its own way, not a moved one that passed",
          got == {"s05": ("picture-top", "light", "a1b2c3d4e5f6")}, got)
    path = os.path.join(tempfile.mkdtemp(prefix="bm_layout_"), "M01_layout_avoid.json")
    b.measure_out(path, got)
    b.measure_out(path, {"s05": ("picture-left", "light", "a1b2c3d4e5f6")})
    b.measure_out(path, got)
    av = json.load(io.open(path, encoding="utf-8"))
    check("each misfit's way joins its slide's list once", av == {"s05": {"words": "a1b2c3d4e5f6", "avoid": [
        ["picture-top", "light"], ["picture-left", "light"]]}}, av)
    b.measure_out(path, {"s05": ("picture-right", "dark", "ffffffffffff")})
    av = json.load(io.open(path, encoding="utf-8"))
    check("... and a slide whose approved words changed starts a new list",
          av["s05"] == {"words": "ffffffffffff", "avoid": [["picture-right", "dark"]]}, av)
    check("one build builds the misfits again at most %d times" % b.LAYOUT_ROUNDS, b.LAYOUT_ROUNDS == 2)


def precheck_part():
    """2.72.5 - the slides built another way for L62 are audited BEFORE the build (layout_precheck): a misfit is measured out
    in seconds instead of a whole LAYOUT round (the figures, the compile, every check) after the build. Replayed on the 2.66
    run's IGF M02 (s04 picture-left did not fit): found by the pre-check in 6 s, the same layouts as the round chose"""
    import io
    import json
    import shutil
    import tempfile
    import test_compile_module as tcm
    import content_script as cs
    tmp = tempfile.mkdtemp(prefix="bm_pre_")
    try:
        words = "The tank connection space holds every valve and flange of the fuel tank, so a leak stays inside it.\n" \
                "• Its ventilation runs all the time.\n• Detectors raise the alarm at 20 % LEL."
        drawn = [{"id": "d%d" % i, "kind": "slide", "title": "Drawing slide %d" % i, "layout": "split", "visual_kind": "schematic",
                  "visual": "The space.", "minutes": 2, "text": words} for i in range(1, 7)]
        c, md = tcm.new_course(tmp, tcm.script(screens=drawn + tcm.SCREENS[-2:]))
        tcm.build_of(c, lambda bs: bs.__setitem__("screens", {x["id"]: {"figure": "ga.html"} for x in drawn}))
        logdir = os.path.join(c, "working_claude", "_build")
        os.makedirs(logdir, exist_ok=True)
        os.makedirs(os.path.join(md, "presentation"), exist_ok=True)
        calls = []

        def audit(page, size, only):               # run_audits.measure's answer: the first slide checked does not fit, once
            deck = io.open(page, encoding="utf-8").read()
            calls.append((size, list(only), os.path.basename(page)))
            sids = [sid for k, (sid, _, _, _) in b.varied_slides(deck) if k in only]
            bad = [] if len(calls) > 2 else [{"slide": only[0] + 1, "id": sids[0], "spill": [{"sel": "div.copy", "px": 31}]}]
            return {"deck": {"exit": 1 if bad else 0, "res": {"failingSlides": bad, "slidesTotal": 8}},
                    "collide": {"exit": 0, "res": {}}, "compose": {"exit": 0, "res": {"screens": 8, "problems": []}}}, ""
        lines, out = b.layout_precheck(c, 1, md, logdir, "M01", [(1280, 800), (1024, 768)], audit)
        first = calls[0][1] if calls else []
        check("only the slides built another way are audited (both sizes at once), before anything is built",
              len(calls) >= 2 and {x[0] for x in calls[:2]} == {(1280, 800), (1024, 768)} and first and len(first) < 8, calls)
        av = json.load(io.open(os.path.join(logdir, "M01_layout_avoid.json"), encoding="utf-8")) \
            if os.path.isfile(os.path.join(logdir, "M01_layout_avoid.json")) else {}
        check("a slide that does not fit is measured out at once (M01_layout_avoid.json, as the end-of-build round writes it)",
              len(out) == 1 and all(av.get(k, {}).get("avoid", [])[:1] == [list(v)] for k, v in out.items()), (out, av))
        check("... the deck is laid out again and only the slides whose way is new are audited (the misfit built its own way, "
              "its neighbours' turn to vary: d3, d5 - never d4 / d6 again) - then it stops (they fit)",
              len(calls) >= 4 and calls[2][1] == calls[3][1] and not set(calls[2][1]) & set(first)
              and "did not fit" in lines[0] and "every one fits" in lines[1], (calls, lines))
        mo = sorted(out)[0]
        before = next((x for x in sorted(av) if x != mo), "")
        check("2.72.7 ... and the L62 repeat that left (%s back on its own way, like the slide before it - measured once more "
              "as it is now) is settled by the layout solver: the slide before it built its next way, both audited at both "
              "sizes, nothing else" % mo,
              len(calls) == 8 and calls[4][1] == calls[5][1] == [first[0]] and any("measured again as now built: %s" % mo in x
                                                                                    for x in lines)
              and calls[6][1] == calls[7][1] == sorted(calls[6][1]) and len(calls[6][1]) == 2
              and any(x.startswith("settled: %s looked like %s (L62)" % (mo, before)) for x in lines)
              and av.get(before, {}).get("avoid") and "the layout solver: 1 settled" in lines[-1], (calls, lines, av))
        check("... the laid-out page is removed", not [f for f in os.listdir(os.path.join(md, "presentation"))
                                                   if f.startswith("_layout_precheck_")], os.listdir(os.path.join(md, "presentation")))
        tcm.run(tcm.COMPILE, c, "--module", "1", "--force")     # the build's compile: it writes M01_layouts.json
        calls.clear()
        lines2, out2 = b.layout_precheck(c, 1, md, logdir, "M01", [(1280, 800), (1024, 768)], audit)
        check("the next build audits nothing: every slide built another way was checked fitting as it is now "
              "(M01_precheck_fit.json)", calls == [] and out2 == {}, (calls, lines2))
        fit = json.load(io.open(os.path.join(logdir, "M01_precheck_fit.json"), encoding="utf-8"))
        held = json.load(io.open(os.path.join(logdir, "M01_layout_avoid.json"), encoding="utf-8"))
        moved = sorted(x for x in fit if x not in held)[0]      # moved by the compiler alone, not by a kept record
        figs = os.path.join(c, "working_claude", "figures", "M01")
        io.open(os.path.join(figs, moved + ".html"), "w", encoding="utf-8").write(        # the same drawing, one part changed
            io.open(os.path.join(figs, "ga.html"), encoding="utf-8").read().replace("</svg>", '<circle cx="9" cy="9" r="3"/></svg>', 1))
        tcm.build_of(c, lambda bs: bs["screens"][moved].__setitem__("figure", moved + ".html"))
        calls.clear()
        b.layout_precheck(c, 1, md, logdir, "M01", [(1280, 800), (1024, 768)], audit)
        check("... but a slide kept its way whose markup changed (2.72.5's timed run: a fixer changed only the drawing on "
              "M02 s04 and it no longer fit) is checked again - only it", len(calls) >= 2 and len(calls[0][1]) == 1
              and calls[0][1] == calls[1][1], (moved, calls))
        src = io.open(os.path.join(HERE, "build_module.py"), encoding="utf-8").read()
        check("build_module.py runs it first (round 0), as a stage of its own, CF_LAYOUT_PRECHECK=off turns it off",
              'timed("layout pre-check (L62)", t0)' in src and "CF_LAYOUT_PRECHECK" in src
              and src.index("layout_precheck(course") < src.index("figure_fit.run_all("), "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def solver_part():
    """2.72.7 - the layout solver: words that do not fit are settled in the pre-check (a wider column, parts, both, its
    other ways), what settles is kept beside the measured-out ways, a try that failed is not made again, and --slides
    checks slides in seconds writing nothing (the 2.72.5 run: M02 s05 over-filled in all 20 builds)"""
    import io
    import json
    import shutil
    import tempfile
    import test_compile_module as tcm
    import compile_module as cm
    print("-- 2.72.7 the layout solver and the slide check")
    tmp = tempfile.mkdtemp(prefix="bm_solve_")
    try:
        words = "The tank connection space holds every valve and flange of the fuel tank.\n" \
                "• Its ventilation runs all the time.\n• Detectors raise the alarm at 20 % LEL.\n• The doors close by themselves."
        drawn = [{"id": "d%d" % i, "kind": "slide", "title": "Drawing slide %d" % i, "layout": "split", "visual_kind": "schematic",
                  "visual": "The space.", "minutes": 2, "text": words} for i in range(1, 5)]
        act = {"id": "a1", "kind": "activity", "title": "Your turn - trace the path", "layout": "split", "visual_kind": "schematic",
               "visual": "The path.", "minutes": 3, "text": words}
        c, md = tcm.new_course(tmp, tcm.script(screens=drawn + [act] + tcm.SCREENS[-2:]))
        tcm.build_of(c, lambda bs: bs.__setitem__("screens", {x["id"]: {"figure": "ga.html"} for x in drawn + [act]}))
        logdir = os.path.join(c, "working_claude", "_build")
        os.makedirs(logdir, exist_ok=True)
        os.makedirs(os.path.join(md, "presentation"), exist_ok=True)
        sheet = os.path.join(c, "working_claude", "script", "M01.build.json")
        sheet0 = io.open(sheet, encoding="utf-8").read()
        calls, rule = [], {}

        def audit(page, size, only):              # run_audits.measure's answer: a slide fits as rule[sid](its section) says
            deck = io.open(page, encoding="utf-8").read()
            calls.append((size, list(only)))
            secs = {k: (sid, x) for k, sid, x in b.slide_order(deck)}
            bad = [{"slide": k + 1, "id": secs[k][0], "scroll": [{"sel": "div.slide-body", "overflowPx": 21}]}
                   for k in only if not rule.get(secs[k][0], lambda x: True)(secs[k][1])]
            return {"deck": {"exit": 1 if bad else 0, "res": {"failingSlides": bad, "slidesTotal": len(secs)}},
                    "collide": {"exit": 0, "res": {}}, "compose": {"exit": 0, "res": {"screens": len(secs), "problems": []}}}, ""
        sizes = [(1280, 800), (1024, 768)]
        rule["d2"] = lambda x: "--lt-text:60" in x                       # fits with the words' column at 60 %
        rule["d3"] = lambda x: 'data-template="content-in-parts.' in x   # fits only in parts
        lines, _ = b.layout_precheck(c, 1, md, logdir, "M01", sizes, audit, extra={"d2", "d3"})
        av = json.load(io.open(os.path.join(logdir, "M01_layout_avoid.json"), encoding="utf-8"))
        check("words that do not fit, found last build: the pre-check measures them first and settles them - d2 with the "
              "words' column at 60 %, d3 in parts after the wider column did not do it",
              any(x.startswith("settled: d2 - its words did not fit; the words' column at 60 %") for x in lines)
              and any(x.startswith("settled: d3 - its words did not fit; its words in parts") for x in lines)
              and av.get("d2", {}).get("set") == {"split": 0.6} and av.get("d3", {}).get("set") == {"template": "content-in-parts"}
              and any("60 %" in t for t in av.get("d3", {}).get("tried", [])), (lines, av))
        check("... each try audited only the slides it changed, at both sizes at once",
              all(calls[k][1] == calls[k + 1][1] and calls[k][0] != calls[k + 1][0] for k in range(0, len(calls), 2))
              and all(len(x[1]) <= 3 for x in calls[2:]), calls)
        script = cm.cs.load(os.path.join(c, "working_claude", "script", "M01.json"))
        page = cm.compile_deck(script, cm.cs.load(sheet), md, os.path.join(c, "working_claude", "figures", "M01"), "x", True,
                               cm.load_layout_avoid(os.path.join(c, "working_claude"), "M01"))[0]
        check("... the compile builds what settled (kept in M01_layout_avoid.json \"set\"); the build sheet is not touched",
              "--lt-text:60" in tcm.section(page, "d2") and 'data-template="content-in-parts.' in tcm.section(page, "d3")
              and io.open(sheet, encoding="utf-8").read() == sheet0, tcm.section(page, "d3")[:300])
        rule["d3"] = lambda x: False                                     # the words changed: nothing fits any more
        calls.clear()
        av0 = json.load(io.open(os.path.join(logdir, "M01_layout_avoid.json"), encoding="utf-8"))
        av0["d3"]["tried"] = ["the words' column at 60 % (\"split\": 0.6)"]
        io.open(os.path.join(logdir, "M01_layout_avoid.json"), "w", encoding="utf-8").write(json.dumps(av0))
        os.remove(os.path.join(logdir, "M01_precheck_fit.json"))
        lines2, _ = b.layout_precheck(c, 1, md, logdir, "M01", sizes, audit, extra={"d3"})
        check("a try made before for the same words is not made again; with every try made, the build says no way was found",
              not any("tried the words' column at 60 % (\"split\": 0.6) on d3" in x for x in lines2)
              and any(x.startswith("d3: no way found that fits") for x in lines2), lines2)
        rule["a1"] = lambda x: False
        calls.clear()
        lines3, _ = b.layout_precheck(c, 1, md, logdir, "M01", sizes, audit, extra={"a1"})
        check("an activity tries the wider column and parts, never another way (the room's task keeps its look)",
              any("on a1" in x for x in lines3) and not any("measured out" in x and "a1" in x for x in lines3)
              and any(x.startswith("a1: no way found") for x in lines3), lines3)
        rule.clear()
        rule["d4"] = lambda x: False
        calls.clear()
        before = io.open(os.path.join(logdir, "M01_layout_avoid.json"), encoding="utf-8").read()
        code, out = b.check_slides(c, 1, ["d1", "d4", "zz"], sizes, audit)
        text = "\n".join(out)
        check("--slides: those slides audited at both sizes in one deck laid out in memory; a misfit and an unknown id said; "
              "what the next build's pre-check would do; nothing written",
              code == 1 and sorted(calls[:2]) == [((1024, 768), [0, 3]), ((1280, 800), [0, 3])] and "zz: not a slide of the deck" in text
              and "d1 - " in text and "fits at 1280x800 and 1024x768" in text and "d4 - " in text and "DOES NOT FIT" in text
              and "nothing written" in text
              and io.open(os.path.join(logdir, "M01_layout_avoid.json"), encoding="utf-8").read() == before
              and not [f for f in os.listdir(os.path.join(md, "presentation")) if f.startswith("_layout_precheck_")], text)
        rule.clear()
        calls.clear()
        page = cm.compile_deck(script, cm.cs.load(sheet), md, os.path.join(c, "working_claude", "figures", "M01"), "x", True,
                               cm.load_layout_avoid(os.path.join(c, "working_claude"), "M01"))[0]
        alone = next(i for i in ("d1", "d2", "d3", "d4") if not any(i in p for p in b.l62_pairs(page)))
        check("... a slide that fits and looks like neither neighbour: exit 0, one audit",
              b.check_slides(c, 1, [alone], sizes, audit)[0] == 0 and len(calls) == 2, calls)
        small_ = lambda px: {"other": ['1024x768 drawing text too small "engine" %s px on screen' % px] * 4}
        check("a try may not leave a slide worse: more findings, or its drawing words smaller (the M02 replay: s04's L62 "
              "settled by a 60 % words' column took its drawing words from 12 to 10.4 px)",
              b.worse(small_(10.4), small_(12)) and not b.worse(small_(12), small_(12)) and b.worse(small_(12), {"other": []})
              and not b.worse({}, small_(12)), "")
        deck_html = '<section class="slide" data-script="s01">a</section><section class="slide" data-script="s02">b</section>' \
                    '<section class="slide" data-script="s03">c</section>'
        check("the build's audits name the next pre-check's slides: scrolls / spills by id, over-filled by number",
              b.fit_misses(deck_html, "  slide 2 (s02): scrolls div.slide-body by 21 px\n  slide 1 (s01): drawing text too small"
                                      "\n  over-filled: 3 (104 %)") == ["s02", "s03"]
              and b.last_misses(logdir, "M09") == "all", b.fit_misses(deck_html, ""))
        src = io.open(os.path.join(HERE, "build_module.py"), encoding="utf-8").read()
        check("build_module.py: the pre-check gets the last build's misfits, the build writes them, and --slides runs "
              "in its own process at once (never beside a running build of the module)",
              "extra=last_misses(logdir, m)" in src and '"%s_fit_misses.json" % m' in src and "check_slides(course, o.module" in src
              and "if slides:" in src, "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def retry_part():
    """2.63.0 - a round that will be built again does not wait for the review sheets or check the package: the moment the
    audits say a slide the compiler moved does not fit, every check still running is ended and the package is not
    started (IGF M01 / M02 v262: retried rounds waited 22-824 s, the sheets holding browser slots the next round needed)"""
    import tempfile
    import time
    tmp = tempfile.mkdtemp(prefix="bm_retry_")
    mark = os.path.join(tmp, "package_ran")
    py = sys.executable
    jobs = {"words (instructor)": [py, "-c", "print('ok')"],
            "audits 1280x800 1024x768": [py, "-c", "import time, sys; time.sleep(1); print('slide 5 (s05): spills'); sys.exit(1)"],
            "review sheets": [py, "-c", "import time; time.sleep(40)"]}
    pkg = [py, "-c", "open(%r, 'w').write('x')" % mark]
    asked = []

    def retry(k, res):
        asked.append(k)
        return {"s05": ("picture-top", "light", "abc")} if k.startswith("audits") and res[0] else None
    t = time.time()
    results, took, again = b.run_checks(jobs, pkg, retry)
    secs = time.time() - t
    check("a round that will retry ends as soon as the audits say so - not after the 40 s review sheets (%.1f s)" % secs,
          secs < 15 and again == {"s05": ("picture-top", "light", "abc")}, (secs, again))
    check("... the package is never checked in that round", "course package" not in results and not os.path.exists(mark), results.keys())
    check("... and the review sheets' answer is not one to read (it was ended)", results.get("review sheets", (0,))[0] != 0, results.get("review sheets"))
    jobs["review sheets"] = [py, "-c", "print('sheets')"]
    results, took, again = b.run_checks(jobs, pkg, lambda k, res: None)
    check("a round that will not retry runs everything and checks the package once the others are done",
          again is None and results["review sheets"][0] == 0 and results["course package"][0] == 0 and os.path.exists(mark), results)


def review_part():
    """2.63.3 (the 2.63.2 full-course run) - the sheets are promoted at module clean, a POLISH.md written into the review
    folder survives the next promotion (five were deleted), and --reviewed makes the sheets just looked at the baseline"""
    import io
    import json
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="bm_review_")
    try:
        out = os.path.join(tmp, "review", "M01")
        os.makedirs(out)
        io.open(os.path.join(out, "POLISH.md"), "w", encoding="utf-8").write("- s03: the label could sit closer\n")
        io.open(os.path.join(out, "manifest.json"), "w", encoding="utf-8").write(json.dumps({"deck/s01": "AAA"}))
        pend = out + ".pending"
        os.makedirs(pend)
        io.open(os.path.join(pend, "manifest.json"), "w", encoding="utf-8").write(json.dumps({"deck/s01": "BBB", "deck/s02": "CCC"}))
        b.promote(pend, out)
        kept = io.open(b.polish_path(out), encoding="utf-8").read() if os.path.isfile(b.polish_path(out)) else ""
        check("a promotion keeps the builder's POLISH list (review\\M01_POLISH.md)", "label could sit closer" in kept, kept)
        check("... and the new sheets replace the folder", json.load(io.open(os.path.join(out, "manifest.json"))) == {"deck/s01": "BBB", "deck/s02": "CCC"})
        b.promote(pend if os.path.isdir(pend) else (os.makedirs(pend) or pend), out)
        check("... a second promotion does not repeat the list", kept == io.open(b.polish_path(out), encoding="utf-8").read())
        check("before --reviewed there is no baseline (every screen is new to the reviewer)", not os.path.isdir(b.reviewed_dir(out)))
        io.open(os.path.join(out, "manifest.json"), "w", encoding="utf-8").write(json.dumps({"deck/s01": "BBB"}))
        code = b.mark_reviewed(out, "M01")
        check("--reviewed copies the sheets' manifest into review\\M01_reviewed, the next comparison's base",
              code == 0 and json.load(io.open(os.path.join(b.reviewed_dir(out), "manifest.json"))) == {"deck/s01": "BBB"})
        src = io.open(b.__file__, encoding="utf-8").read()
        check("the review sheets compare with the reviewed baseline and keep their pictures in _build\\MNN_shots",
              '"--base=" + reviewed_dir(out_dir)' in src and '"%s_shots" % m' in src)
        check("a parallel build promotes at module clean (only the course package left)",
              'clean = passed or (o.no_course_pages and fails == ["course package"])' in src)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def long_part():
    """2.63.3 - a build that runs past the shell's limit is not lost: it answers STILL BUILDING (exit 3) and goes on; --wait
    prints its own answer; a second build of the same module waits for the running one (IGF 2.63.2: M01's first build took
    1,076 s, the builder's 600 s shell call ended with no answer)"""
    import subprocess
    import tempfile
    import shutil
    import time
    tmp = tempfile.mkdtemp(prefix="bm_long_")
    try:
        course = os.path.join(tmp, "course")
        for d in ("modules", "working_claude"):
            os.makedirs(os.path.join(course, d))
        env = dict(os.environ, CF_BUILD_ANSWER_WITHIN="2", CF_BUILD_TEST_SLEEP="7")
        cmd = [sys.executable, "-I", os.path.join(HERE, "build_module.py"), course, "--module", "1"]
        run = lambda extra=(): subprocess.run(cmd + list(extra), capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        t = time.time()
        p = run()
        check("a build past its answer time says STILL BUILDING and exits 3 within it (%.1f s)" % (time.time() - t),
              p.returncode == 3 and "STILL BUILDING M01" in p.stdout and time.time() - t < 6, (p.returncode, p.stdout, p.stderr[-300:]))
        p2 = run()
        check("... a second build of the module waits for the running one instead of starting another",
              "already running" in p2.stdout, (p2.returncode, p2.stdout))
        env["CF_BUILD_ANSWER_WITHIN"] = "30"
        p3 = run(["--wait"])
        check("... --wait prints the build's own answer and its exit code (here: no module folder - Stopped, 2)",
              p3.returncode == 2 and "Stopped" in p3.stdout, (p3.returncode, p3.stdout, p3.stderr[-300:]))
        env["CF_BUILD_TEST_SLEEP"] = "0"
        p4 = run()
        check("a quick build answers at once, as before", p4.returncode == 2 and "Stopped" in p4.stdout and "STILL" not in p4.stdout,
              (p4.returncode, p4.stdout))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
