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
    beside the last trial's, each number that moved said better or worse.
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
