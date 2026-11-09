# -*- coding: utf-8 -*-
"""test_factory_trial - a few modules of a real course built from scratch after an update, and scored (factory_trial.py).

    python test_factory_trial.py

Pinned:
  * setup remembers the course's inputs and copies only its decisions, the course named FACTORY TRIAL; a course without
    its source_files, old course or intake is refused;
  * run makes a new trial course: the marker, source_files and the old course LINKED (never copied), the decisions in
    working_claude, the prompt naming the trial's modules; a second run deletes the first - and the real source_files and
    old course behind the links are untouched; a folder without the marker is never deleted;
  * a trial signs its own STOPs ("Factory trial") only with NOVIKONTAS_TRIAL=1 and the marker; course_portal.py refuses
    a trial course - it never goes to the training app;
  * run starts Claude Code (a stub here) unattended in the trial course, then scores it; the scorecard is saved and set
    beside the last trial's, each number that moved said better or worse;
  * on a small built deck: passed (PASS or MODULE CLEAN) and the minutes to the first PASS from the build's own files;
    the slides cut at 1280x800 and 1024x768 from one fit_gate.py run; the slides off their blueprint (an unknown template,
    version or variant, a picture slot empty or a placeholder); pictures still placeholders; the 3D share as the course
    package counts it; the words the room sees at once (the longest part, never the compiler's own words); a number that
    cannot be measured is None;
  * report --course scores any trial course and saves only where --run says; --against and compare set two scorecards
    side by side; nearer the 3D band is better.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import factory_trial as ft  # noqa: E402

PASS, FAIL = [], []
W = lambda n: " ".join(["word"] * n)
BTN = '<div class="mediabar"><button class="fbtn" data-act="next">Next step <svg viewBox="0 0 24 24"></svg></button></div>'
DECK = """<!doctype html><html><body>
<section class="slide" id="s01" data-kind="Theory" data-visual="model_3d" data-template="content-in-parts.v1" data-variant="with-figure"
 data-cue="{w30}"><div class="slide-kind"><b>Theory</b> M01 1 / 7</div><h2 data-script-field="title">Three word title</h2>
 <div class="fill fig"><img src="../assets/img/m01_s01.jpg">{btn}</div>
 <div class="lt-parts"><div class="lt-part on" data-part="1"><p data-script-field="text">{w30}</p></div>
 <div class="lt-part" data-part="2"><p data-script-field="text">{w50}</p></div></div></section>
<section class="slide" id="s02" data-kind="Theory" data-visual="photo" data-template="photo-explain.v1" data-variant="column">
 <h2>Placeholder</h2><img src="../assets/img/_placeholder_s02.png"></section>
<section class="slide" id="s03" data-kind="Theory" data-visual="photo" data-template="made-up.v1" data-variant="x"><img src="a.jpg"></section>
<section class="slide" id="s04" data-kind="Theory" data-visual="photo" data-template="explain-figure.v2" data-variant="figure-right"><img src="a.jpg"></section>
<section class="slide" id="s05" data-kind="Theory" data-visual="photo" data-template="content-in-parts.v1" data-variant="figure-left">
 <h2>No picture</h2>{btn}</section>
<section class="slide" id="s06" data-kind="Theory" data-visual="none" data-template="explain-figure.v1" data-variant="text-only">
 <h2 data-script-field="title">{w10}</h2><ol><li><span class="n" data-script-ignore>1</span><p data-script-field="text">{w120}</p></li></ol>
 <div class="lt-ans-over" data-script-ignore><p>{w20}</p></div><svg><text>label words</text></svg></section>
<section class="slide activity" id="t01" data-kind="Task" data-visual="none" data-template="task-launch.v1" data-variant="room"><p>{w10}</p></section>
<script>var words = "{w50}";</script>
</body></html>""".format(btn=BTN, **{"w%d" % n: W(n) for n in (10, 20, 30, 50, 120)})


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def cli(*args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ft.main(list(args))
    return code, buf.getvalue()


def main():
    tmp = tempfile.mkdtemp(prefix="trial_")
    old_env = dict(os.environ)
    try:
        src = os.path.join(tmp, "GAS BASIC")
        for d in ("source_files", "old_course", os.path.join("course", "working_claude")):
            os.makedirs(os.path.join(src, d))
        io.open(os.path.join(src, "source_files", "programme.txt"), "w").write("the programme")
        io.open(os.path.join(src, "old_course", "deck.txt"), "w").write("the old deck")
        wc = os.path.join(src, "course", "working_claude")
        io.open(os.path.join(wc, "intake.json"), "w", encoding="utf-8").write(json.dumps({
            "course_name": "GAS BASIC 04/11", "knowledge_base": {"path": "D:/KB"},
            "asked": [{"question": "course name in the training app", "answer": "GAS BASIC 04/11"}]}))
        io.open(os.path.join(wc, "kb_sources.json"), "w", encoding="utf-8").write(json.dumps({"knowledge_base": "D:/KB"}))
        home = os.path.join(tmp, "home")

        print("-- setup")
        bad = os.path.join(tmp, "empty")
        os.makedirs(bad)
        code, out = cli("setup", "--home", home, "--from", bad)
        check("a folder without the course's inputs is refused", code == 2 and "source_files" in out, out)
        code, out = cli("setup", "--home", home, "--from", src, "--modules", "1,4,8,19")
        cfg = json.load(io.open(os.path.join(home, "trial.json"), encoding="utf-8"))
        intake = json.load(io.open(os.path.join(home, "decisions", "intake.json"), encoding="utf-8"))
        check("setup remembers the inputs and the modules", code == 0 and cfg["modules"] == [1, 4, 8, 19]
              and cfg["inputs"]["old_course"].endswith("old_course") and cfg["inputs"]["knowledge_base"] == "D:/KB", (out, cfg))
        check("... and copies the decisions, the course named FACTORY TRIAL", intake["course_name"] == "FACTORY TRIAL"
              and intake["asked"][0]["answer"] == "FACTORY TRIAL" and os.path.isfile(os.path.join(home, "decisions", "kb_sources.json")), intake)

        print("\n-- run")
        code, out = cli("run", "--home", home, "--modules", "1,4", "--dry-run")
        master = os.path.join(home, "run", "FACTORY TRIAL")
        check("run makes the trial course with its marker and decisions", code == 0 and os.path.isfile(os.path.join(master, ft.MARKER))
              and os.path.isfile(os.path.join(master, "course", "working_claude", "intake.json")), out)
        check("... source_files and the old course are linked, not copied",
              ft.is_link(os.path.join(master, "source_files")) and ft.is_link(os.path.join(master, "old_course"))
              and io.open(os.path.join(master, "old_course", "deck.txt")).read() == "the old deck")
        runs = sorted(os.listdir(os.path.join(home, "runs")))
        prompt = io.open(os.path.join(home, "runs", runs[-1], "prompt.txt"), encoding="utf-8").read()
        check("... the prompt names the trial's modules, its signer and that the training app is never called",
              "Only modules 1, 4 get" in prompt and '--by "Factory trial"' in prompt and "Never call course_portal.py" in prompt, prompt)
        io.open(os.path.join(master, "course", "working_claude", "left_over.txt"), "w").write("x")
        code, out = cli("run", "--home", home, "--dry-run")
        check("a second run starts from an empty course again", code == 0 and not os.path.isfile(os.path.join(master, "course", "working_claude", "left_over.txt")), out)
        check("... and the real source_files and old course behind the links are untouched",
              io.open(os.path.join(src, "source_files", "programme.txt")).read() == "the programme"
              and io.open(os.path.join(src, "old_course", "deck.txt")).read() == "the old deck")
        try:
            ft.remove_run(src)
            refused = False
        except OSError:
            refused = True
        check("a folder without the trial's marker is never deleted", refused and os.path.isdir(src))

        print("\n-- the trial's guards")
        course = os.path.join(master, "course")
        os.environ.pop("NOVIKONTAS_TRIAL", None)
        check("without NOVIKONTAS_TRIAL the trial signs nothing", cs.unattended_signer(course) != "Factory trial")
        os.environ["NOVIKONTAS_TRIAL"] = "1"
        check("with it and the marker, every STOP is signed \"Factory trial\"", cs.unattended_signer(course) == "Factory trial")
        os.environ["NOVIKONTAS_AUTO_BUILD"] = "1"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cs.cmd_approve(course, 1, "a writer")
        check("an approval by another name is refused with the name to use, not with the expert's Ready (the factory trial's "
              "writers were told every row was unanswered)", code == 1 and '--by "Factory trial"' in buf.getvalue()
              and "Ready" not in buf.getvalue(), buf.getvalue())
        os.environ.pop("NOVIKONTAS_AUTO_BUILD", None)
        os.environ.pop("NOVIKONTAS_TRIAL", None)
        import course_portal
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = course_portal.main(["status", "--course", course])
        check("course_portal.py refuses a trial course - it never goes to the training app", code == 2 and "factory trial" in buf.getvalue(), buf.getvalue())

        print("\n-- run, unattended, then the scorecard")
        os.environ["NOVIKONTAS_CLAUDE_CMD"] = json.dumps([sys.executable, "-c", "import os; print('trial', os.environ.get('NOVIKONTAS_TRIAL')); print('TRIAL DONE')"])
        code, out = cli("run", "--home", home, "--modules", "1")
        runs = sorted(os.listdir(os.path.join(home, "runs")))
        log = io.open(os.path.join(home, "runs", runs[-1], "build.log"), encoding="utf-8").read()
        check("run starts Claude Code in the trial course, unattended and marked a trial", "trial 1" in log and "TRIAL DONE" in log, log)
        card = json.load(io.open(os.path.join(home, "runs", runs[-1], "scorecard.json"), encoding="utf-8"))
        check("... then scores each trial module", [r["module"] for r in card["modules"]] == [1] and card["modules"][0]["built"] is False, card)
        before = {"plugin": "2.105.0", "modules": [{"module": 1, "cut_or_cropped_slides": 9, "claims_unproven": 0, "templates": 5}]}
        now = {"modules": [{"module": 1, "cut_or_cropped_slides": 1, "claims_unproven": 3, "templates": 5}]}
        moved = ft.compare(now, before)
        check("the scorecard says what moved since the last trial: fewer cut slides better, more unproven claims worse",
              (1, "cut_or_cropped_slides", 9, 1, "better") in moved and (1, "claims_unproven", 0, 3, "worse") in moved and len(moved) == 2, moved)
        code, out = cli("status", "--home", home)
        check("status lists the trial and its runs", code == 0 and "run(s)" in out and "modules 1, 4, 8, 19" in out, out)

        print("\n-- the scorecard's numbers, on a small built deck")
        other = os.path.join(tmp, "other home", "run", "FACTORY TRIAL")
        oc = os.path.join(other, "course")
        deck = os.path.join(oc, "modules", "module01", "presentation", "index.html")
        os.makedirs(os.path.dirname(deck))
        os.makedirs(os.path.join(oc, "working_claude", "_build"))
        io.open(os.path.join(other, ft.MARKER), "w", encoding="utf-8").write(json.dumps({"trial": True, "modules": [1], "plugin": "9.9.9",
                                                                                          "started": "2026-11-09 10:00"}))
        io.open(deck, "w", encoding="utf-8").write(DECK)
        slides = {s["id"]: s for s in ft.scan_deck(deck)}
        check("the words the room sees at once: the longest part, not every part; no header band, step number, button or "
              "answer shown twice", slides["s01"]["seen_words"] == 3 + 50 and slides["s06"]["seen_words"] == 130,
              {k: (v["seen_words"], v["words"], v["parts"]) for k, v in slides.items()})
        off = ft.off_blueprint(list(slides.values()))
        check("off its blueprint: an unknown template, a template's wrong version, a picture slot with a placeholder or no "
              "picture - and nothing else", off == ["s02", "s03", "s04", "s05"], off)
        check("interactive 3D counted as the course package counts it (L67): 1 of the 6 teaching slides", ft.three_d_share(deck) == 17)
        build = os.path.join(oc, "working_claude", "_build")
        io.open(os.path.join(build, "M01_answer.txt"), "w", encoding="utf-8").write(
            "FAIL M01 - course package (80 s)\nMODULE CLEAN - only the course package is left\nFull log: x\n")
        io.open(os.path.join(build, "M01_clock.json"), "w", encoding="utf-8").write(json.dumps({"started": 1, "passed": 2, "minutes": 37}))
        row = ft.score_module(oc, 1, no_browser=True)
        check("a module scored: passed (MODULE CLEAN), its verdict, its minutes to the first PASS, off-blueprint slides, "
              "pictures still placeholders, the 3D share, the most words and the slides over 120; no browser, no fit numbers",
              row["passed"] is True and row["build_says"].startswith("MODULE CLEAN") and row["build_minutes"] == 37
              and row["off_blueprint_slides"] == 4 and row["pictures_pending"] == 1 and row["interactive_3d_share"] == 17
              and row["max_words_slide"] == 130 and row["slides_over_120_words"] == 1
              and row["cut_or_cropped_slides"] is None and row["cut_at_1024x768"] is None, row)
        io.open(os.path.join(build, "M01_answer.txt"), "w", encoding="utf-8").write("FAIL M01 - figures (80 s)\nFull log: x\n")
        io.open(os.path.join(build, "M01_clock.json"), "w", encoding="utf-8").write(json.dumps({"started": 1}))
        row = ft.score_module(oc, 1, no_browser=True)
        check("... a FAIL did not pass, and a clock with no PASS has no minutes", row["passed"] is False and row["build_minutes"] is None
              and row["build_says"].startswith("FAIL M01"), row)
        check("a number that cannot be measured is None, never a stop", ft.measured(lambda: 1 / 0) is None)

        class FakeFit:
            @staticmethod
            def main(args):
                io.open(args[args.index("--json") + 1], "w", encoding="utf-8").write(json.dumps(
                    {"1280x800": [["s01", 1, "cut", "a"], ["s01", 2, "cut", "b"]], "1024x768": [["s01", 1, "cut", "a"], ["s05", 1, "picture", "c"]]}))
                return 1
        sys.modules["fit_gate"] = FakeFit
        try:
            fit = ft.fit_slides(deck, False)
        finally:
            sys.modules.pop("fit_gate", None)
        check("fit_gate at 1280x800 and 1024x768 in one run: the slides cut at each size", fit == {"1280x800": 1, "1024x768": 2}, fit)

        sc = os.path.join(tmp, "scored")
        code, out = cli("report", "--course", oc, "--no-browser", "--run", sc)
        card = json.load(io.open(os.path.join(sc, "scorecard.json"), encoding="utf-8"))
        check("report --course scores any trial course, saved only where --run says", code == 0 and card["plugin"] == "9.9.9"
              and card["modules"][0]["off_blueprint_slides"] == 4 and "off blueprint slides" in out and "max words slide" in out
              and not os.path.isfile(os.path.join(oc, "scorecard.json")), out)
        older = os.path.join(tmp, "older.json")
        io.open(older, "w", encoding="utf-8").write(json.dumps({"plugin": "9.9.8", "modules": [
            {"module": 1, "passed": True, "off_blueprint_slides": 6, "interactive_3d_share": 17, "max_words_slide": 90}]}))
        code, out = cli("report", "--course", oc, "--no-browser", "--against", older)
        check("report --against sets it beside another scorecard, side by side", code == 1 and "before 9.9.8" in out
              and "now 9.9.9" in out and "M01 passed" in out and "WORSE" in out and "not saved" in out, out)
        code, out = cli("compare", older, os.path.join(sc, "scorecard.json"))
        check("compare sets two scorecards side by side, each number that moved better or worse",
              code == 1 and "off blueprint slides     6" in out and "M01 off blueprint slides     6 -> 4  better" in out
              and "M01 max words slide          90 -> 130  WORSE" in out, out)
        code, out = cli("compare", older)
        check("compare without two scorecards stops", code == 2 and "two scorecard.json" in out, out)
        moved = ft.compare({"modules": [{"module": 1, "interactive_3d_share": 65, "passed": False, "build_minutes": 30}]},
                           {"modules": [{"module": 1, "interactive_3d_share": 40, "passed": True, "build_minutes": 45}]})
        check("closer to the 60-80 % band of 3D is better, a module that no longer passes worse, fewer minutes better",
              (1, "interactive_3d_share", 40, 65, "better") in moved and (1, "passed", True, False, "worse") in moved
              and (1, "build_minutes", 45, 30, "better") in moved, moved)
        moved = ft.compare({"modules": [{"module": 1, "interactive_3d_share": 75}]}, {"modules": [{"module": 1, "interactive_3d_share": 70}]})
        check("... and inside the band neither", moved == [(1, "interactive_3d_share", 70, 75, "-")], moved)
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        master = os.path.join(tmp, "home", "run", "FACTORY TRIAL")
        if os.path.isdir(master):
            ft.remove_run(master)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
