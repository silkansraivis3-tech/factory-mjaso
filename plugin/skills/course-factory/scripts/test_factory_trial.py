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
import subprocess
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
        os.environ["NOVIKONTAS_CLAUDE_CMD"] = json.dumps([sys.executable, "-c", "import os; print('trial', os.environ.get('NOVIKONTAS_TRIAL')); "
                                                          "print('libraries', os.environ.get('NOVIKONTAS_COURSE_LIBRARIES'), "
                                                          "os.environ.get('NOVIKONTAS_SUBJECT_LIBRARIES')); print('TRIAL DONE')"])
        code, out = cli("run", "--home", home, "--modules", "1")
        runs = sorted(os.listdir(os.path.join(home, "runs")))
        log = io.open(os.path.join(home, "runs", runs[-1], "build.log"), encoding="utf-8").read()
        check("run starts Claude Code in the trial course, unattended and marked a trial", "trial 1" in log and "TRIAL DONE" in log, log)
        check("... with the shared course libraries off - a trial never writes to them (the factory trial: subject_library.py "
              "ensure would have written to the shared Drive)", "libraries off off" in log, log)
        sys.path.insert(0, os.path.join(ft.PLUGIN, "skills", "course-visuals", "scripts"))
        import subject_library
        lib_code, lib_res = subject_library.ensure("Liquefied gas tanker cargo operations", env=dict(os.environ, **ft.LIBRARIES_OFF))
        check("... and with them off, subject_library.py ensure finds no place to write", lib_code == 3 and lib_res["parent"] is None
              and lib_res["created"] == [], lib_res)
        card = json.load(io.open(os.path.join(home, "runs", runs[-1], "scorecard.json"), encoding="utf-8"))
        check("... then scores each trial module", [r["module"] for r in card["modules"]] == [1] and card["modules"][0]["built"] is False, card)
        before = {"plugin": "2.105.0", "modules": [{"module": 1, "cut_or_cropped_slides": 9, "claims_unproven": 0, "templates": 5}]}
        now = {"modules": [{"module": 1, "cut_or_cropped_slides": 1, "claims_unproven": 3, "templates": 5}]}
        moved = ft.compare(now, before)
        check("the scorecard says what moved since the last trial: fewer cut slides better, more unproven claims worse",
              (1, "cut_or_cropped_slides", 9, 1, "better") in moved and (1, "claims_unproven", 0, 3, "worse") in moved and len(moved) == 2, moved)
        code, out = cli("status", "--home", home)
        check("status lists the trial and its runs", code == 0 and "run(s)" in out and "modules 1, 4, 8, 19" in out, out)

        print("\n-- the log as the run goes, and a run that ends on the usage limit")
        cmd = ft.claude_command("p")
        check("claude -p runs as an event stream", cmd[cmd.index("--output-format") + 1] == "stream-json" and "--verbose" in cmd, cmd)
        ev = lambda **k: json.dumps(k)
        import time
        seen = {"start": time.time() - 245 * 60}
        shown = [ft.readable(ev(type="assistant", message={"content": [{"type": "text", "text": "The M19 build is running."},
                                                                         {"type": "tool_use", "name": "Agent", "input": {"description": "QA M19"}}]}), seen),
                 ft.readable(ev(type="assistant", parent_tool_use_id="t1", message={"content": [{"type": "text", "text": "inside a helper"}]}), seen),
                 ft.readable(ev(type="user", message={"content": []}), seen),
                 ft.readable(ev(type="result", num_turns=234, duration_ms=14700000, total_cost_usd=36.4, result="TRIAL STOPPED: x"), seen),
                 ft.readable("You've hit your 5-hour limit\n", seen)]
        check("the log shows the session's words, each agent it starts, the minutes since the start and the cost so far - never a "
              "helper's own stream", shown[0] == "The M19 build is running.\n  > Agent: QA M19" and shown[1] is None and shown[2] is None
              and shown[3] == "(245 min since the start, $36 so far in this claude -p)\n\nTRIAL STOPPED: x"
              and shown[4] == "You've hit your 5-hour limit", shown)
        # print mode sends every turn's result when the run ends, each with that run's cost: the 2.126.0 trial's log said
        # "(the session: 2 turns, 0 min, $61)" 36 times over 2.7 hours - the minutes of one turn and the same cost
        late = [ft.readable(ev(type="result", num_turns=2, duration_ms=9000, total_cost_usd=36.4, result=r), seen)
                for r in ("The M19 build is running.", "TRIAL STOPPED: x", "")]
        check("... the results that come together at the end show nothing new: no line for a turn's own minutes, the same cost "
              "or an answer the log already has", late == [None, None, None], late)
        check("... a result whose answer the log has not shown yet shows it, under the minutes since the start",
              ft.readable(ev(type="result", total_cost_usd=36.4, result="Module 1 passes."), seen)
              == "(245 min since the start, $36 so far in this claude -p)\n\nModule 1 passes.")
        logf = os.path.join(tmp, "live.log")
        stub = [sys.executable, "-c", "import json, sys, time; print(json.dumps({'type': 'assistant', 'message': {'content': "
                "[{'type': 'text', 'text': 'first words'}]}})); sys.stdout.flush(); time.sleep(1); "
                "print('seen' if 'first words' in open(sys.argv[1], encoding='utf-8').read() else 'not yet')", logf]
        rc = ft.run_claude(stub, tmp, dict(os.environ), logf)
        check("each line reaches the log while the run is still going (the trial's log was written only at its end)",
              rc == 0 and io.open(logf, encoding="utf-8").read() == "first words\nseen\n", io.open(logf, encoding="utf-8").read())

        # the 2.126.0 trial: two helpers ended their turns while their own 3D checks still ran, the session had nothing
        # running and claude -p quit at 18:26 without TRIAL DONE / TRIAL STOPPED - M19's post-fix build and M01's fix round lost
        fake = os.path.join(tmp, "fake_claude.py")
        io.open(fake, "w", encoding="utf-8").write(
            "import json, os, sys\n"
            "a = sys.argv[1:]\n"
            "io = open(os.environ['FAKE_CALLS'], 'a', encoding='utf-8'); io.write(json.dumps(a) + '\\n'); io.close()\n"
            "sid = a[a.index('--resume') + 1] if '--resume' in a else 'sess-1'\n"
            "say = lambda t: print(json.dumps({'type': 'assistant', 'session_id': sid, 'message': {'content': [{'type': 'text', 'text': t}]}}))\n"
            "print(json.dumps({'type': 'system', 'subtype': 'init', 'session_id': sid}))\n"
            "mode = os.environ['FAKE_MODE']\n"
            "if mode == 'limit':\n    say(\"You've hit your 5-hour limit\")\n"
            "elif mode == 'quits' and '--resume' in a:\n    say('Module 19 passes.'); say('TRIAL DONE')\n"
            "else:\n    say('Both 3D checks are still running. Waiting.')\n"
            "print(json.dumps({'type': 'result', 'session_id': sid, 'total_cost_usd': 61.1, 'result': 'Waiting.'}))\n")
        calls = os.path.join(tmp, "calls.jsonl")
        base = [sys.executable, fake, "-p", "the trial prompt", "--permission-mode", "acceptEdits"]

        def resumed_run(mode):
            if os.path.isfile(calls):
                os.remove(calls)
            rc = ft.run_claude(base, tmp, dict(os.environ, FAKE_CALLS=calls, FAKE_MODE=mode), logf)
            return rc, [json.loads(x) for x in io.open(calls, encoding="utf-8")], io.open(logf, encoding="utf-8").read()
        rc, argv, log = resumed_run("quits")
        check("a run that quits without its last line is carried on in the same session (--resume <its id from the stream>), "
              "with a short carry-on prompt and the same flags, in the same log, said in a line",
              rc == 0 and len(argv) == 2 and argv[0] == base[2:] and argv[1][:2] == ["-p", ft.course_portal.CARRY_ON]
              and argv[1][2:4] == ["--resume", "sess-1"] and argv[1][4:] == base[4:]
              and "carried on in the same session, 1 of 3" in log and log.rstrip().endswith("TRIAL DONE")
              and log.index("Waiting.") < log.index("carried on") < log.index("Module 19 passes."), (argv, log))
        check("... the carry-on prompt says that a helper waiting on its own background work has stopped, and to end with the "
              "same one line", "waiting on its own background work has stopped" in ft.course_portal.CARRY_ON.replace("\n", " ")
              and "same one line" in ft.course_portal.CARRY_ON)
        rc, argv, log = resumed_run("never")
        check("... at most 3 times: then it stops as it is", len(argv) == 4 and log.count("carried on in the same session") == 3
              and "3 of 3" in log, (len(argv), log))
        rc, argv, log = resumed_run("limit")
        check("... never after Claude's usage limit (it is scored as such)", len(argv) == 1 and "carried on" not in log, (argv, log))
        os.environ["NOVIKONTAS_CLAUDE_CMD"] = json.dumps([sys.executable, fake])
        os.environ.update(FAKE_CALLS=calls, FAKE_MODE="quits")
        os.remove(calls)
        code, out = cli("run", "--home", home, "--modules", "1")
        runs = sorted(os.listdir(os.path.join(home, "runs")))
        log = io.open(os.path.join(home, "runs", runs[-1], "build.log"), encoding="utf-8").read()
        check("factory_trial.py run carries the session on and ends on its line", "carried on in the same session, 1 of 3" in log
              and "The build said: TRIAL DONE" in out and len(io.open(calls, encoding="utf-8").readlines()) == 2, (out, log))
        for k in ("NOVIKONTAS_CLAUDE_CMD", "FAKE_CALLS", "FAKE_MODE"):
            os.environ.pop(k, None)
        check("a run whose last lines say Claude's usage limit stopped it", ft.stopped_by("M04 fix round running\nYou've hit your "
              "5-hour limit · resets 1:50pm (Europe/Riga)\n") == "usage limit" and ft.stopped_by("TRIAL DONE\n") is None)
        os.environ["NOVIKONTAS_CLAUDE_CMD"] = json.dumps([sys.executable, "-c", "print('TRIAL STOPPED: usage limit reached.'); "
                                                          "print(\"You've hit your 5-hour limit\")"])
        code, out = cli("run", "--home", home, "--modules", "1")
        runs = sorted(os.listdir(os.path.join(home, "runs")))
        card = json.load(io.open(os.path.join(home, "runs", runs[-1], "scorecard.json"), encoding="utf-8"))
        check("... is scored \"stopped: usage limit\" - its modules unfinished, not failed (the trial's scorecard read as four "
              "failed modules)", code == 1 and card.get("stopped") == "usage limit" and "STOPPED: usage limit" in out
              and "Module 1 - stopped: usage limit, unfinished" in out, out)
        check("... and the scorecard counts the simulator drafts still awaiting the course director",
              card["modules"][0].get("simulator_drafts_pending") == 0, card["modules"][0])
        node = shutil.which("node")
        if node:
            core = os.path.join(ft.PLUGIN, "skills", "course-tablet-publisher", "vendor", "package-core.mjs").replace("\\", "/")
            p = subprocess.run([node, "--input-type=module", "-e", "const m = await import('file:///%s'); console.log(m.slug(%s))"
                                % (core.lstrip("/"), json.dumps(ft.TITLE))], capture_output=True, text=True)
            check("the trial's course name makes a classroom course ID with no space (the importer's \"The course ID must be a "
                  "unique name without spaces\" was COURSE.html not yet written, never the name)",
                  p.stdout.strip() == "factory-trial", (p.stdout, p.stderr))

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
        # the 2.126.0 trial scored M01 s28 and s28b off their blueprint: each holds a 2D-kit figure, which kit2d.js draws when
        # the page opens - the scorecard saw no picture in the page as written, and the build never judged blueprints
        k2 = ('<section class="slide" id="s28" data-kind="Theory" data-visual="comparison" data-template="worked-example.v1" '
              'data-variant="figure"><h2>Which tanks need a secondary barrier</h2><div class="lt-scol"><div class="lt-in fill fig '
              'kit2d-fig" data-script-ignore><div class="kit2d-stage" data-kit2d="#k2-s28"></div><script type="application/json" '
              'id="k2-s28">{"parts":[{"id":"N1","type":"node"}]}</script></div></div></section>')
        bare = k2.replace('<div class="kit2d-stage" data-kit2d="#k2-s28"></div>', "")
        import check_course_package as ccp
        k2deck = os.path.join(tmp, "k2deck.html")
        offs = []
        for page in (k2, bare):
            io.open(k2deck, "w", encoding="utf-8").write("<!doctype html><html><body>%s</body></html>" % page)
            offs.append((ft.off_blueprint(ft.scan_deck(k2deck)), ccp.off_blueprint(ccp.deck_slides(ccp.parse(k2deck)))))
        check("a 2D-kit figure is the picture its template needs - for the scorecard and for the build's course package check "
              "alike; the same slide with no figure is off its blueprint for both", offs == [([], []), (["s28"], ["s28"])], offs)
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
        check("the shapes the eye sees, beside the templates: how many (a picture left or right is one shape, beside), the "
              "longest run of one shape, and the share of beside - 4 of the 5 teaching slides here",
              row["look_shapes"] == 2 and row["same_look_in_a_row"] == 2 and row["beside_share"] == 80
              and "same_template_in_a_row" in row, row)
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
                    {"1280x800": [["s01", 1, "cut", "a"], ["s01", 2, "cut", "b"], ["s23", 1, "dead", "d"]],
                     "1024x768": [["s01", 1, "cut", "a"], ["s05", 1, "picture", "c"], ["s23", 1, "dead", "d"], ["s09", 1, "twice", "e"]]}))
                return 1
        sys.modules["fit_gate"] = FakeFit
        try:
            fit = ft.fit_slides(deck, False)
        finally:
            sys.modules.pop("fit_gate", None)
        check("fit_gate at 1280x800 and 1024x768 in one run: the slides cut at each size - a drawing that never changes and lines "
              "walked twice are no cut slide (the 2.127.0 trial's M01 s23 was counted cut at both sizes)",
              fit == {"1280x800": 1, "1024x768": 2}, fit)

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
