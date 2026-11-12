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
    side by side; nearer the 3D band is better;
  * reuse: a stage's hashes move only with what it reads (a section of a guide, a script it runs, not a test); a run keeps
    the last run's Stage 1-3 before deleting it and takes them only while every file they read is unchanged (by the hashes
    the trial recorded, or the commit its version names) AND the copy passes this factory's gate and approval - else the
    stage runs, its copy taken out and the decisions put back; the prompt, the run's lines and the scorecard say which and
    why; --fresh takes nothing; setup --reuse <an earlier trial> keeps its stages, --dry-run only says what it would take.
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

        print("\n-- the trial's modules: one with practical work, unless told")
        gas = os.path.join(tmp, "GAS PRACTICAL")
        for d in ("source_files", "old_course"):
            os.makedirs(os.path.join(gas, d))
        gw = os.path.join(gas, "course", "working_claude")
        os.makedirs(gw)
        shutil.copy2(os.path.join(wc, "intake.json"), gw)
        topics = {str(n): {"title": "Topic %d" % n, "theory": 2, "practical": 0} for n in range(1, 20)}
        topics["8"]["practical"] = topics["16"]["practical"] = 2
        topics["16"]["theory"] = 0.25
        dump = lambda name, obj: io.open(os.path.join(gw, name), "w", encoding="utf-8").write(json.dumps(obj))
        dump("programme.json", {"title": "Basic training for liquefied gas tanker cargo operations", "academic_hour_min": 40, "topics": topics})
        dump("plan.json", {"modules": [{"module": n, "topics": [str(n)], "built_min": 40 * (topics[str(n)]["theory"] + topics[str(n)]["practical"])}
                                       for n in range(1, 20)]})
        dump("architecture.json", {"course": {"title": "Basic training"}, "modules": [
            {"module": 8, "practicals": [{"task": "Portable gas detectors: bump test", "equipment": "portable gas detectors"}]},
            {"module": 16, "practicals": [{"task": "Foam applicator on a liquid fire", "equipment": "gas-fire simulation equipment, hoses"}]}]})
        home2 = os.path.join(tmp, "home2")
        code, out = cli("setup", "--home", home2, "--from", gas)
        cfg2 = json.load(io.open(os.path.join(home2, "trial.json"), encoding="utf-8"))
        check("setup without --modules builds the first module and the cheapest one with practical work (the 2.128 trial's "
              "modules 1 and 19 had none: no paper exercise was ever built)", code == 0 and cfg2["modules"] == [1, 16], (out, cfg2))
        code, out = cli("setup", "--home", home2, "--from", gas, "--modules", "1,19")
        check("... modules given by hand that build no practical work are said, with the one that would",
              code == 0 and "Modules 1, 19 have no simulator or equipment exercise" in out and "M16 would" in out, out)
        arch = json.load(io.open(os.path.join(gw, "architecture.json"), encoding="utf-8"))
        arch["modules"].append({"module": 4, "practicals": [{"task": "Loading on the LPG cargo handling simulator", "equipment": "LCHS"}]})
        dump("architecture.json", arch)
        check("... a simulator exercise comes before real equipment", ft.default_modules(os.path.join(gas, "course")) == [1, 4],
              ft.default_modules(os.path.join(gas, "course")))
        dump("architecture.json", {"course": {"title": "Basic training"}, "modules": []})
        for t in topics.values():
            t["practical"] = 0
        dump("programme.json", {"title": "Project management", "academic_hour_min": 40, "topics": topics})
        check("... a course with no practical work: the first and the middle module", ft.default_modules(os.path.join(gas, "course")) == [1, 10]
              and ft.lane_note(os.path.join(gas, "course"), [1, 19]) is None, ft.default_modules(os.path.join(gas, "course")))

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
        check("... the build's helpers come from brief.mjs, the trial's rules in its notes, and the session explores nothing",
              "helpers come from brief.mjs" in prompt and "list no folders and read no factory script's source" in prompt
              and "only catalogues the old course's own photographs" in prompt and "--none" not in prompt, prompt)
        check("... the default run is the first pass: one rewrite round, a capped build, nothing fixed after, first_pass.json kept; "
              "the marker says so", "FIRST PASS" in prompt and "ONE rewrite round" in prompt and '"first_pass": true' in prompt
              and '"builds": 3' in prompt and "--despite-findings" in prompt and "first_pass.json" in prompt
              and "full trial" not in prompt and ft.load(os.path.join(master, ft.MARKER))["first_pass"] is True, prompt)
        code, out = cli("run", "--home", home, "--modules", "1,4", "--dry-run", "--full")
        full_prompt = io.open(os.path.join(home, "runs", sorted(os.listdir(os.path.join(home, "runs")))[-1], "prompt.txt"), encoding="utf-8").read()
        check("... --full keeps today's build, with its fix round", code == 0 and "full trial" in full_prompt
              and "FIRST PASS" not in full_prompt and ft.load(os.path.join(master, ft.MARKER))["first_pass"] is False, full_prompt)
        cli("run", "--home", home, "--modules", "1,4", "--dry-run")
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
        check("... and says the course's practical work, here none: \"No practical work in this course\"",
              (card.get("practical") or [""])[0].startswith("No practical work in this course") and "Practical work in the course:" in out
              and card["modules"][0].get("practical_kind") == "none", (card.get("practical"), out[-600:]))
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
        check("a full trial's module has no first-pass lines", "first_pass_clean" not in row and "builds_used" not in row, row)
        agents = os.path.join(build, "agents")
        os.makedirs(agents, exist_ok=True)
        io.open(os.path.join(oc, "working_claude", "first_pass.json"), "w", encoding="utf-8").write(json.dumps({"scripts": {"1": {
            "rewrite_rounds": 1, "must_fixes_first_check": 4, "approved_clean": False, "open_must_fixes": ["s05: a task is not covered"]}}}))
        io.open(os.path.join(agents, "result.json"), "w", encoding="utf-8").write(json.dumps({"first_pass": {"builds_cap": 3, "modules": [
            {"module": "1", "builds": 3, "first_build": "FAIL M01 - figures (80 s)", "clean": False, "findings_total": 4,
             "findings": {"overflow_cut": 2, "three_d": 1, "script": 1, "words": 0}}]}}))
        row = ft.score_module(oc, 1, no_browser=True)
        check("first-pass lines: script rewrite rounds, must-fixes at the first check, the script not approvable (with its open "
              "must-fixes), builds used, the first build's verdict, the findings of the first review by kind, and clean: no",
              row["script_rewrite_rounds"] == 1 and row["must_fixes_first_check"] == 4
              and row["script_approved_first_pass"].startswith("no - open: s05") and row["builds_used"] == 3
              and row["first_build_verdict"].startswith("FAIL M01") and row["first_review_findings"] == "overflow/cut 2, 3D 1, script 1"
              and row["first_review_findings_total"] == 4 and row["first_pass_clean"] == "no", row)
        shown_out = io.StringIO()
        with contextlib.redirect_stdout(shown_out):
            ft.show({"plugin": "x", "modules": [dict(row, module=1)]})
        check("... and the scorecard prints them", "first pass clean" in shown_out.getvalue() and "first review findings" in shown_out.getvalue(),
              shown_out.getvalue())
        io.open(os.path.join(oc, "working_claude", "first_pass.json"), "w", encoding="utf-8").write(json.dumps({"scripts": {"1": {
            "rewrite_rounds": 0, "must_fixes_first_check": 0, "approved_clean": True, "open_must_fixes": []}}}))
        io.open(os.path.join(agents, "result.json"), "w", encoding="utf-8").write(json.dumps({"first_pass": {"modules": [
            {"module": "1", "builds": 1, "first_build": "PASS M01", "clean": True, "findings_total": 0, "findings": {}}]}}))
        row = ft.score_module(oc, 1, no_browser=True)
        check("... a script approved at once and a build with nothing found at the first review: clean yes",
              row["first_pass_clean"] == "yes" and row["first_review_findings"] == "none" and row["script_approved_first_pass"] == "yes", row)

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
        reuse_part(tmp, src)
        faults_part(tmp)
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        for h in ("home", "home2", "home3"):
            master = os.path.join(tmp, h, "run", "FACTORY TRIAL")
            if os.path.isdir(master):
                ft.remove_run(master)
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


def faults_part(tmp):
    """the fault report: rule checks on a built deck, the fit gate's cuts, the judges' fails, and the page for the owner"""
    import fault_report as fr
    from PIL import Image
    print("\n-- the fault report")
    course = os.path.join(tmp, "fr", "course")
    pres = os.path.join(course, "modules", "module01", "presentation")
    os.makedirs(os.path.join(pres, "..", "assets", "img"))
    Image.new("RGB", (300, 200)).save(os.path.join(pres, "..", "assets", "img", "wide.jpg"))      # 1.50:1
    Image.new("RGB", (200, 300)).save(os.path.join(pres, "..", "assets", "img", "tall.jpg"))      # 0.67:1
    Image.new("RGB", (250, 250)).save(os.path.join(pres, "..", "assets", "img", "square.jpg"))
    words = " ".join(["word"] * 90)

    def slide(sid, tid, var, img, text):
        return ('<section class="slide" id="%s" data-template="%s.v1" data-variant="%s"><h2>T</h2><img src="../assets/img/%s">'
                '<p>%s</p></section>' % (sid, tid, var, img, text))
    page = "<html><body>%s</body></html>" % (slide("s01", "explain-figure", "figure-right", "wide.jpg", "a few words")
                                              + slide("s02", "photo-explain", "column", "square.jpg", "a few words")
                                              + slide("s03", "photo-explain", "column", "tall.jpg", words))
    io.open(os.path.join(pres, "index.html"), "w", encoding="utf-8").write(page)
    deck = os.path.join(pres, "index.html")
    slides = ft.scan_deck(deck)
    found = fr.rule_checks(deck, slides)
    by = {(f["slide"], f["kind"]): f for f in found}
    check("a photograph in a blueprint that takes none is a layout fault, with the rule, its file and what it did",
          ("s01", "layout") in by and "takes no photo" in by[("s01", "layout")]["did"]
          and "explain-figure.figure-right" in by[("s01", "layout")]["source"] and "1.50:1" in by[("s01", "layout")]["did"] and "a photograph" in by[("s01", "layout")]["did"], found)
    check("... a photograph inside its blueprint's box, and words inside its budget, are no fault", not any(f["slide"] == "s02" for f in found), found)
    check("... a slide over its blueprint's word budget is a words fault with the numbers",
          ("s03", "words") in by and "against" in by[("s03", "words")]["did"], found)
    check("... a picture outside the box's shape range names the range",
          ("s03", "layout") in by and "outside 0.85-1.3:1" in by[("s03", "layout")]["did"], found)

    def titled(sid, tid, var, img, text, cls="slide"):
        return ('<section class="%s" id="%s" data-template="%s.v1" data-variant="%s"><h2 data-script-field="title">Chlorine ships '
                'and LPG chemical ships</h2><div class="fill fig"><img src="../assets/img/%s"></div><p data-script-field="text">%s</p>'
                '</section>' % (cls, sid, tid, var, img, text))
    one = os.path.join(pres, "one.html")
    io.open(one, "w", encoding="utf-8").write("<html><body>%s</body></html>" % (
        titled("s08", "photo-explain", "column", "square.jpg", " ".join(["word"] * 82))
        + titled("s06", "explain-figure", "figure-top", "wide.jpg", " ".join(["word"] * 65), cls="slide dark")
        + titled("s09", "photo-explain", "column", "wide.jpg", "a few words", cls="slide photo")
        + titled("s10", "photo-explain", "column", "square.jpg", "a few words")))
    sl = ft.scan_deck(one)
    found1 = fr.rule_checks(one, sl)
    by1 = {(f["slide"], f["kind"]): f for f in found1}
    check("the words a budget counts are the text's, the title apart, as measure_word_budgets.py measured them: 82 words "
          "under a 6-word title beside a photo column (85) are no fault (the 2.131.0 trial's M01 s08: '87 against 85')",
          {s["id"]: s["text_words"] for s in sl}["s08"] == 82 and ("s08", "words") not in by1, (sl, found1))
    check("... and the budget is the blueprint's measured one, never its template's word range: 65 words under a band of "
          "photographs (70) are no fault (the trial's '65 against 60 in explain-figure.figure-top')", ("s06", "words") not in by1, found1)
    check("... a slide whose section has more classes (dark, photo) is read on its own: its picture is judged, and the slide "
          "before it does not take its photograph", ("s09", "layout") in by1 and "1.50:1" in by1[("s09", "layout")]["did"]
          and ("s10", "layout") not in by1 and ("s06", "layout") not in by1, found1)
    fit = fr.fit_faults({"1024x768": [["s03", 2, "cut", "the table is cut by 66 px"], ["s03", 2, "static", "a drawing never changes"]]}, None)
    check("the fit gate's cuts are overflow faults at the size they were found (its other findings are none)",
          len(fit) == 1 and fit[0]["kind"] == "overflow_cut" and "1024x768" in fit[0]["found_by"] and "66 px" in fit[0]["did"], fit)
    check("... with no browser, the build's own list of slides it measured out", fr.fit_faults({}, ["s09"])[0]["slide"] == "s09")
    agents = os.path.join(course, "working_claude", "_build", "agents")
    os.makedirs(agents)
    io.open(os.path.join(agents, "walk_1.json"), "w", encoding="utf-8").write(json.dumps({"fails": [
        {"slide": "s04", "what": "stop 3: the chart is cut off at the right edge"}, {"slide": "tasks/q2", "what": "the answer boxes overlap"}]}))
    io.open(os.path.join(agents, "qa_1.json"), "w", encoding="utf-8").write(json.dumps({"findings": [
        {"severity": "BROKEN", "where": "SCRIPT: s05", "what": "a Your turn activity counts 5 practice minutes"},
        {"severity": "POLISH", "where": "s02", "what": "a label could sit closer"}]}))
    walk = os.path.join(course, "working_claude", "_build", "walk", "M01")
    os.makedirs(walk)
    for n in ("s04_k1.png", "s04_k3.png", "s01_k1.png"):
        Image.new("RGB", (40, 30)).save(os.path.join(walk, n))
    judged = fr.judge_faults(course, 1)
    kinds = sorted((f["slide"], f["kind"]) for f in judged)
    check("the judges' fails: the walk's (a task page apart), QA's BROKEN script finding; a POLISH line is no fault",
          kinds == [("s04", "overflow_cut"), ("s05", "script"), ("tasks/q2", "task_page")], kinds)
    run = os.path.join(tmp, "fr", "run")
    os.makedirs(run)
    allf = fr.collect(course, [1], {1: (deck, slides, {"1280x800": [["s04", 3, "cut", "the chart is cut"]]})})
    path = fr.write(run, allf)
    data = json.load(io.open(os.path.join(run, "faults.json"), encoding="utf-8"))
    pics = {f["slide"]: f["picture"] for f in data if f["picture"]}
    check("the report: faults.json, FAULTS.html, the pictures copied beside it (the stop the judge named), each fault with an "
          "empty decision",
          os.path.isfile(path) and pics.get("s04") == "faults/M01_s04_s04_k3.png" and os.path.isfile(os.path.join(run, pics["s04"]))
          and pics.get("s01") == "faults/M01_s01_s01_k1.png" and all(f["decision"] == "" and f["rule"] and f["did"] and f["source"] for f in data), data)
    page = io.open(path, encoding="utf-8").read()
    check("... the page is self-contained: relative picture links, the rule, what it did, the decision field, no script",
          'src="faults/M01_s04' in page and "The rule" in page and "What it did" in page and "Owner" in page and "<script" not in page
          and "http" not in page.replace("https://", ""), page[:300])


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True)


def reuse_part(tmp, src):
    """a release that changes only the build takes the last trial's Stage 1-3 - and only then"""
    print("\n-- reuse: the last trial's Stage 1-3, when nothing they read changed")
    text = "front\n## The brief\nbrief words\n## The gate\ngate words\n## Building\nbuild words\n"
    check("a guide's section runs from its heading to the next; the part before the first; a heading not there is None",
          ft.section(text, "The gate") == "## The gate\ngate words" and ft.section(text, "") == "front"
          and ft.section(text, "Stage 3") is None)
    plug = os.path.join(tmp, "plug")
    skill = os.path.join(plug, "skills", "course-factory")
    write(os.path.join(plug, ".claude-plugin", "plugin.json"), '{"version": "1.0.0"}')
    write(os.path.join(skill, "SKILL.md"), text)
    write(os.path.join(skill, "scripts", "content_script.py"), "# the script checks\n")
    write(os.path.join(skill, "coverage", "scripts", "sim_coverage.py"), "# simulators\n")
    write(os.path.join(skill, "coverage", "scripts", "test_sim_coverage.py"), "# a test\n")
    h1 = {s: ft.stage_hashes(ft.OnDisk(plug), s) for s in ft.STAGES}
    write(os.path.join(skill, "SKILL.md"), text.replace("build words", "other build words"))
    write(os.path.join(skill, "coverage", "scripts", "test_sim_coverage.py"), "# another test\n")
    write(os.path.join(skill, "SKILL.md.bak"), "x")
    h2 = {s: ft.stage_hashes(ft.OnDisk(plug), s) for s in ft.STAGES}
    check("a section a stage does not read, a test or a file not on the list changes no stage", h1 == h2,
          [(s, k) for s in h1 for k in h1[s] if h1[s][k] != h2[s][k]])
    write(os.path.join(skill, "SKILL.md"), text.replace("gate words", "the gate, said otherwise"))
    write(os.path.join(skill, "scripts", "content_script.py"), "# a new must-fix\n")
    h3 = {s: ft.stage_hashes(ft.OnDisk(plug), s) for s in ft.STAGES}
    check("... a section it reads, or a script it runs, changes that entry alone",
          [k for k in h1["read"] if h1["read"][k] != h3["read"][k]] == ["skills/course-factory/SKILL.md#The gate"]
          and [k for k in h1["script"] if h1["script"][k] != h3["script"][k]] == ["skills/course-factory/scripts/content_script.py"],
          [(s, k) for s in h1 for k in h1[s] if h1[s][k] != h3[s][k]])
    check("every entry of the stage lists names a file or folder of the factory as it is now (a renamed file would never "
          "match again, silently)", all(ft.OnDisk(ft.PLUGIN).read(e.split("#")[0]) is not None
                                        or ft.OnDisk(ft.PLUGIN).files(e.split("#")[0]) for s in ft.STAGES for e in ft.STAGES[s]),
          [e for s in ft.STAGES for e in ft.STAGES[s] if ft.OnDisk(ft.PLUGIN).read(e.split("#")[0]) is None
           and not ft.OnDisk(ft.PLUGIN).files(e.split("#")[0])])
    real = {s: ft.stage_hashes(ft.OnDisk(ft.PLUGIN), s) for s in ft.STAGES}
    check("... and every section named is in its guide", not [e for s in ft.STAGES for e in ft.STAGES[s] if real[s][e] == "missing"],
          [e for s in ft.STAGES for e in ft.STAGES[s] if real[s][e] == "missing"])

    kept = os.path.join(tmp, "kept")
    write(os.path.join(kept, "course", "working_claude", "script", "M01.json"), "{}")
    mark = {"plugin": "1.0.0", "started": "2026-11-11 02:13", "modules": [1, 19], "factory": {"commit": "", "stages": h3}}
    write(os.path.join(kept, ft.MARKER), json.dumps(mark))
    plan = ft.decide(kept, [1, 4], plug)
    check("decide: both stages taken when every file they read is as it was, the scripts only of modules the last trial "
          "scripted", plan["read"]["reuse"] and plan["script"]["reuse"] and plan["script"]["modules"] == [1]
          and "unchanged (by the hashes it recorded)" in plan["read"]["why"], plan)
    write(os.path.join(skill, "scripts", "content_script.py"), "# yet another must-fix\n")
    plan = ft.decide(kept, [1, 4], plug)
    check("... a script the stage runs changed: that stage runs, its why names the file",
          plan["read"]["reuse"] and not plan["script"]["reuse"] and plan["script"]["changed"] == ["skills/course-factory/scripts/content_script.py"]
          and "content_script.py" in plan["script"]["why"], plan)
    write(os.path.join(skill, "SKILL.md"), text)
    plan = ft.decide(kept, [1, 4], plug)
    check("... Stage 1-2 runs: the scripts, written against it, run too", not plan["read"]["reuse"] and not plan["script"]["reuse"]
          and "#The gate" in plan["read"]["why"] and "Stage 1-2, which runs" in plan["script"]["why"], plan)
    plan = ft.decide(kept, [1], plug, fresh=True)
    check("... --fresh runs every stage; no earlier trial, the same", not plan["read"]["reuse"] and "--fresh" in plan["read"]["why"]
          and not ft.decide(os.path.join(tmp, "nothing"), [1], plug)["read"]["reuse"], plan)

    print("   (a trial before the hashes: its version's commit)")
    write(os.path.join(skill, "SKILL.md"), text)
    write(os.path.join(skill, "scripts", "content_script.py"), "# the script checks\n")
    ok = git(plug, "init", "-q").returncode == 0
    if ok:
        git(plug, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
        git(plug, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "1.0.0")
        write(os.path.join(plug, ".claude-plugin", "plugin.json"), '{"version": "1.1.0"}')
        write(os.path.join(skill, "scripts", "content_script.py"), "# 1.1.0 checks more\n")
        git(plug, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "1.1.0")
        old = dict(mark, factory=None)
        write(os.path.join(kept, ft.MARKER), json.dumps(old))
        plan = ft.decide(kept, [1], plug)
        check("an old trial with no hashes is matched by its version to the one commit that says it: what changed since runs, "
              "the rest is taken", plan["read"]["reuse"] and "matched by its version 1.0.0" in plan["read"]["why"]
              and plan["script"]["changed"] == ["skills/course-factory/scripts/content_script.py"], plan)
        write(os.path.join(kept, ft.MARKER), json.dumps(dict(old, plugin="0.9.0")))
        plan = ft.decide(kept, [1], plug)
        check("... a version no commit says: nothing is taken, and it says why", not plan["read"]["reuse"]
              and "names 0 commit(s)" in plan["read"]["why"], plan)
    else:
        check("git is on this computer (the version match needs it)", False)

    print("   (a run takes them, judged by this factory)")
    home = os.path.join(tmp, "home2")
    code, out = cli("setup", "--home", home, "--from", src, "--modules", "1,4")
    code, out = cli("run", "--home", home, "--dry-run")
    master = os.path.join(home, "run", "FACTORY TRIAL")
    first = json.load(io.open(os.path.join(master, ft.MARKER), encoding="utf-8"))
    check("a run records the factory it ran - its commit and each stage's hashes - and that it took nothing, the first time",
          set(first["factory"]["stages"]) == set(ft.STAGES) and not first["reused"]["read"]["reuse"]
          and "no earlier trial" in first["reused"]["read"]["why"] and "RUNS   Stage 1-2" in out, (first.get("reused"), out))
    wc = os.path.join(master, "course", "working_claude")
    write(os.path.join(wc, "architecture.json"), '{"modules": []}')
    write(os.path.join(wc, "intake.json"), '{"course_name": "FACTORY TRIAL", "knowledge_base_decision": {"answer": "yes"}}')
    write(os.path.join(wc, "ilo_map.json"), json.dumps({"rows": [
        {"module": "M01", "sub_ilo_id": "1.a", "where_taught": "slide 3", "taught_on": ["s03"]},
        {"module": "M04", "sub_ilo_id": "4.a", "where_taught": "slide 5", "checked_on": ["q01"]}]}))
    for f in ("script/M01.json", "fact_check/M01.json", "task_cover/M01.json", "script/M04.build.json"):
        write(os.path.join(wc, f), '{"module": 1}')
    write(os.path.join(wc, "COURSE_STATE.md"), "built - every module done")
    real_check = ft.check_copied
    said = {"gate": [], "modules": {"1": []}}
    ft.check_copied = lambda course, mods, plugin_dir=None: {"gate": said["gate"], "modules": {str(m): said["modules"].get(str(m), []) for m in mods}}
    try:
        code, out = cli("run", "--home", home, "--dry-run")
        mark2 = json.load(io.open(os.path.join(master, ft.MARKER), encoding="utf-8"))
        prompt = io.open(os.path.join(home, "runs", sorted(os.listdir(os.path.join(home, "runs")))[-1], "prompt.txt"), encoding="utf-8").read()
        wc2 = os.path.join(master, "course", "working_claude")
        ilo = json.load(io.open(os.path.join(wc2, "ilo_map.json"), encoding="utf-8"))
        check("the next run keeps the last one's stages before deleting it, and takes them: Stage 1-2 and module 1's script with "
              "its fact check and task cover - never a build sheet or the old run's state of the course",
              mark2["reused"]["read"]["reuse"] and mark2["reused"]["script"]["modules"] == [1]
              and all(os.path.isfile(os.path.join(wc2, f)) for f in ("architecture.json", "script/M01.json", "fact_check/M01.json",
                                                                      "task_cover/M01.json"))
              and not os.path.isfile(os.path.join(wc2, "script", "M04.build.json"))
              and "every module done" not in io.open(os.path.join(wc2, "COURSE_STATE.md"), encoding="utf-8").read()
              and os.path.isfile(os.path.join(home, ft.REUSE, ft.MARKER)), (mark2.get("reused"), os.listdir(wc2)))
        check("... the ILO map keeps the slides and questions of module 1's script, not of module 4's, which is written again",
              ilo["rows"][0].get("where_taught") == "slide 3" and "where_taught" not in ilo["rows"][1] and "checked_on" not in ilo["rows"][1], ilo)
        check("... the prompt says Stage 1-2 and module 1's script are done, and only module 4 gets a script",
              "Stage 1 and Stage 2 are DONE" in prompt and "content scripts of modules 1 are DONE" in prompt
              and "Only modules 4 get a content script" in prompt and "cover the whole programme" not in prompt, prompt)
        check("... and the run says so: REUSED and why, a line a stage", "REUSED Stage 1-2" in out and "REUSED the content scripts "
              "(written, task-covered, fact-checked, approved) of modules 1 - from the trial of" in out, out)
        lines = io.StringIO()
        with contextlib.redirect_stdout(lines):
            ft.show({"plugin": "x", "modules": [], "reused": mark2["reused"]})
        check("... and so does the scorecard", "Taken from the last trial" in lines.getvalue() and "REUSED Stage 1-2" in lines.getvalue(),
              lines.getvalue())

        said["modules"] = {"1": ["q02: the answer is not proved in the sources"]}
        code, out = cli("run", "--home", home, "--dry-run")
        mark3 = json.load(io.open(os.path.join(master, ft.MARKER), encoding="utf-8"))
        wc3 = os.path.join(master, "course", "working_claude")
        check("a copied script this factory would not approve is taken out again and written: the run says which and why",
              mark3["reused"]["read"]["reuse"] and not mark3["reused"]["script"]["reuse"]
              and not os.path.isfile(os.path.join(wc3, "script", "M01.json")) and "q02: the answer is not proved" in out, (mark3["reused"], out))

        said["gate"] = ["The operator has not approved the Stage 2 page yet"]
        code, out = cli("run", "--home", home, "--dry-run")
        mark4 = json.load(io.open(os.path.join(master, ft.MARKER), encoding="utf-8"))
        intake = json.load(io.open(os.path.join(master, "course", "working_claude", "intake.json"), encoding="utf-8"))
        check("a copy that does not pass the gate is taken out again - the decisions back as setup copied them - and Stage 1-2 runs",
              not mark4["reused"]["read"]["reuse"] and "does not pass the gate" in mark4["reused"]["read"]["why"]
              and not os.path.isfile(os.path.join(master, "course", "working_claude", "architecture.json"))
              and "knowledge_base_decision" not in intake and intake["course_name"] == "FACTORY TRIAL", (mark4["reused"], intake))
        said["gate"] = []
        code, out = cli("run", "--home", home, "--dry-run", "--fresh")
        mark5 = json.load(io.open(os.path.join(master, ft.MARKER), encoding="utf-8"))
        check("--fresh takes nothing", not mark5["reused"]["read"]["reuse"] and "--fresh" in out, out)
    finally:
        ft.check_copied = real_check
    gate = ft.check_copied(os.path.join(master, "course"), [])
    check("the real check judges a copy by the gate of the factory that builds: an architecture never approved does not pass",
          gate["gate"] and any("approved" in x or "architecture" in x for x in gate["gate"]), gate)

    print("   (setup --reuse an earlier trial)")
    old_run = os.path.join(home, "runs", "20200101-0000_0.1.0")
    os.makedirs(old_run)
    code, out = cli("setup", "--home", os.path.join(tmp, "home3"), "--reuse", old_run)
    check("a run folder that is not its home's last run is refused: only the last run's course is kept",
          code == 2 and "not its home's last run" in out, out)
    code, out = cli("setup", "--home", os.path.join(tmp, "home3"), "--reuse", home, "--dry-run")
    check("setup --reuse --dry-run says what a run would take, and writes nothing",
          code == 0 and "Nothing written" in out and "Stage 1-2" in out and not os.path.exists(os.path.join(tmp, "home3")), out)
    code, out = cli("setup", "--home", os.path.join(tmp, "home3"), "--reuse", home)
    cfg3 = json.load(io.open(os.path.join(tmp, "home3", "trial.json"), encoding="utf-8"))
    check("setup --reuse takes the earlier trial's course and modules, and keeps its stages for the next run",
          code == 0 and cfg3["modules"] == [1, 4] and os.path.isfile(os.path.join(tmp, "home3", ft.REUSE, ft.MARKER))
          and "Kept for the next run" in out, out)


if __name__ == "__main__":
    sys.exit(main())
