#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The factory trial - a few modules of a real course built from scratch after every major update, and scored.

    factory_trial.py setup  --from <course master folder> [--modules 1,16] [--home <folder>]
    factory_trial.py setup  --reuse <an earlier trial's home or run> [--from ...] [--plugin-dir <plugin folder>] [--dry-run]
    factory_trial.py run    [--modules 1,4] [--plugin-dir <plugin folder>] [--fresh] [--dry-run] [--home <folder>]
    factory_trial.py report [--run <runs\\folder>] [--course <trial course>] [--against <scorecard.json>] [--no-browser] [--home <folder>]
    factory_trial.py compare <scorecard.json before> <scorecard.json now>
    factory_trial.py status [--home <folder>]

WHY THIS EXISTS
To see whether a release builds courses better, a whole course was built - hours of work, and every run asked other
questions and made other choices, so two runs could not be compared. The trial keeps one course's inputs (its
source_files, old course and knowledge base, read where they are) and its decisions (intake.json, kb_sources.json), and
builds only a few modules - by default two: the first, and the cheapest one with simulator or real-equipment exercises
(sim_coverage.py practical; a simulator before equipment), so the paper exercises are built in every trial - from an
empty folder, unattended, the way the office PC builds. Then it scores what was built and sets the score beside the last
trial's. Modules given by hand that build no practical work in a course that has some are said, on setup and on run.

  setup   remembers the course's inputs and copies its decision files (course name "FACTORY TRIAL"). Nothing is copied
          from the inputs: source_files and the old course are linked into each run (the factory only reads them, L14).
  run     deletes the last trial course - only a folder that carries FACTORY_TRIAL.json, and its links are removed as
          links, never their targets - makes a new one, and starts Claude Code in it (claude -p, the course-factory
          skill, its "Auto build" rules, NOVIKONTAS_TRIAL=1). Every STOP is signed "Factory trial"; the training app is
          never called; no paid picture is made; nothing is pushed; the shared course libraries are off (nothing is
          written outside the trial folder). --plugin-dir builds with a plugin checkout instead of
          the installed one (a release before it is pushed); --modules builds only some of the trial's modules (a retest
          of two). The log and the score go to runs\\<date>\\ - the log line by line as the run goes (the session's words,
          each agent it starts, the minutes since the start and the cost so far). A run that ends without its last line
          and not on the usage limit is carried on in the same session (claude -p --resume), up to 3 times, in the same
          log. Then report.
          REUSE: a release that changes only the build need not pay for the intake, the Stage 2 page and the scripts
          again. A run takes them from the last trial (the home's last run, or the trial setup --reuse named) when every
          factory file the stage reads (STAGES, in one place below) is what it was when that trial ran - by the hashes
          the trial recorded, or for a trial before them by the commit its version names - and the copied files still pass
          the stage's own checks with this factory: the gate (course_gate.py) for Stage 1-2, approval for a script (no
          must-fix, its claims proved, its questions covered - content_script.approval_blockers). Anything else, and
          --fresh, runs the stage. The prompt, the marker and the scorecard say which stage was reused and why.
  report  the scorecard of each trial module, and what changed since the last trial:
            built, passed (its last build said PASS or MODULE CLEAN) and that build's verdict; minutes to its first PASS
            (the build's clock, cf_timing.py); slides cut or pictures cropped at 1280 x 800 and at 1024 x 768, every Next
            pressed (fit_gate.py); slides off their blueprint - not a known template, version and variant
            (course-module-ui knowledge/blueprints/, layout-templates.json), or a picture slot with no picture or a placeholder;
            picture spaces still holding a placeholder; % of the teaching slides with interactive 3D (L67, counted as the
            course package counts it); the most words the room sees at once on one slide, and the slides over 120; claims
            not proved in the sources (fact_check.py); old-course findings (order, slides left out, thinner theory); Bloom
            lifts of more than one level; must-fix findings left in the script; how many slide templates and the longest
            run of one; how many shapes the eye sees (layout-templates.json "shapes": a picture left or right is one,
            beside), the longest run of one shape and the share of beside; the basic tasks of each self-check and the self-checks off their mix (t_sc_mix); simulator and
            equipment exercises written, and simulator drafts still awaiting the course director (L66); over the modules, the
            course's practical work module by module, or "No practical work in this course". A number that
            cannot be measured is "-". A run that ended on Claude's usage limit is scored "stopped: usage limit": its
            modules are unfinished, not failed.
          --course scores any trial course (its master or course folder) - two trial homes compared; the scorecard is
          saved only where --run says. --against sets it beside that scorecard instead of the last trial's.
  compare two scorecards side by side, and each number that moved said better or worse.
  status  the trial's inputs and its last runs.

The trial lives in %USERPROFILE%\\factory-trial (NOVIKONTAS_TRIAL_HOME, or --home). Exit 0, 1 problems, 2 bad input.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "compile", "scripts"))
import layout_plan  # noqa: E402  - the shapes the eye sees, read the way the compiler plans them
import course_portal  # noqa: E402
import workspace  # noqa: E402

TITLE = "FACTORY TRIAL"
MARKER = "FACTORY_TRIAL.json"
SIGNER = "Factory trial"
DECISIONS = ("intake.json", "kb_sources.json")
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
# the school's shared course libraries are outside the trial folder: subject_library.py ensure / contribute would write
# there, so a trial runs with them off (course-visuals/scripts/subject_library.py: "off" = no library at all)
LIBRARIES_OFF = {"NOVIKONTAS_COURSE_LIBRARIES": "off", "NOVIKONTAS_SUBJECT_LIBRARIES": "off"}

TRIAL_PROMPT = """You are the NOVIKONTAS course factory on a FACTORY TRIAL: a test build of a few modules after a factory update.
Nobody is there to answer. The course in this folder is "FACTORY TRIAL"; its source_files, old course and knowledge base are
here, and its decisions are already in course/working_claude (intake.json, kb_sources.json) - do not ask them again.
Use the course-factory skill and build it by its "Auto build" rules (SKILL.md), with these differences:
{stages}
{flow}
- There is no expert: sign every STOP --by "Factory trial" (NOVIKONTAS_TRIAL=1 allows it). Never call course_portal.py -
  a trial never goes to the training app.
- Generate no paid pictures or videos; fill picture spaces from the free sources, and a space nobody could fill keeps its
  brief. Never push to git and never change a file outside this folder: a temporary file or a command's saved output goes
  in course/working_claude/scratch, never /tmp or the system temp folder. The shared course libraries are off for a trial
  (NOVIKONTAS_COURSE_LIBRARIES=off) - nothing is read from or saved to them.
- The build's helpers come from brief.mjs (SKILL.md Auto build); the "notes" of its args.json carry the picture and folder
  rules above, word for word. Run the photo pass it lists (photos:course, photos:drafts)
  as it says, but in a trial it only catalogues the old course's own photographs (index, assign) and makes no picture.
- This folder and the factory are as said here and in SKILL.md: list no folders and read no factory script's source (its
  --help says how to run it).
End with one line: TRIAL DONE, or TRIAL STOPPED: <why>."""
FIRST_PASS = """- THIS TRIAL MEASURES THE FACTORY'S FIRST PASS: what it makes by itself, not what helpers can repair. Nothing loops.
  Scripts: the writer writes each script once; the task-coverage-checker, the fact-checker and the approval check run once
  (`content_script.py status` lists the must-fixes). At most ONE rewrite round to clear the must-fixes, then the checks once
  more. Then approve it as it stands (`approve --by "Factory trial"`), or - when must-fixes are still open - approve it with
  `--despite-findings` (the build goes on, so the build stage is measured too) and record it as not approvable on the first
  pass. Write `working_claude/first_pass.json` as you go: {"scripts": {"<module number>": {"rewrite_rounds": 0 or 1,
  "must_fixes_first_check": <count at the first check>, "approved_clean": true/false, "open_must_fixes": ["<where: what>", ...]}}}.
  Build: in args.json for brief.mjs set "first_pass": true and "builds": 3. Each module gets Phase A and at most 3 builder
  builds, no carry-on builder, no fix round, no polish round and no second walk - the 3D check, QA and the walk review run
  once on that build and their findings are recorded in result.json, not fixed. Fix nothing yourself after the build:
  a module that is not clean is the result. Report it as it is."""
FULL_RUN = """- This is the full trial (--full): the build keeps its fix round, its polish round and the walk's second look, as a real
  course build does."""
FRESH = """- Stage 1 and Stage 2 cover the whole programme as usual. Only modules {modules} get a content script, the fact-checker,
  a build and its checks; leave every other module unscripted."""
READ_REUSED = """- Stage 1 and Stage 2 are DONE and approved, taken from the last trial ({why}): do not run them again. COURSE_STATE.md and
  FEEDBACK_LOG.md are new; say there that Stage 1-2 came from the last trial."""
SCRIPTS_REUSED = """- The content scripts of modules {done} are DONE - approved, fact-checked and task-covered, taken from the last trial the
  same way: do not write, check or approve them again; build them."""
SCRIPTS_TO_WRITE = """- Only modules {modules} get a content script, the fact-checker, a build and its checks; leave every other module
  unscripted."""


def home_of(given=None):
    return os.path.abspath(given or os.environ.get("NOVIKONTAS_TRIAL_HOME") or os.path.join(os.path.expanduser("~"), "factory-trial"))


def load(p, default=None):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(json.dumps(data, ensure_ascii=False, indent=1))


def modules_of(text):
    try:
        out = [int(x) for x in str(text).replace(" ", "").split(",") if x]
    except ValueError:
        return []
    return out if out and all(x > 0 for x in out) else []


def plugin_version(plugin_dir=None):
    d = load(os.path.join(plugin_dir or PLUGIN, ".claude-plugin", "plugin.json"), {}) or {}
    return d.get("version", "?")


def master_and_course(source):
    master = os.path.abspath(workspace.master_of(source) if hasattr(workspace, "master_of") else source)
    return master, os.path.join(master, "course") if os.path.isdir(os.path.join(master, "course")) else master


def sim_cov():
    """coverage/scripts/sim_coverage.py - which modules have simulator or equipment exercises (L66)"""
    cov = os.path.join(os.path.dirname(HERE), "coverage", "scripts")
    if cov not in sys.path:
        sys.path.insert(0, cov)
    import sim_coverage
    return sim_coverage


RANK = {"simulator": 0, "equipment": 1, "room": 2, "unnamed": 3}
DEFAULT_MODULES = [1, 4, 8, 19]          # a course whose plan and programme cannot be read


def default_modules(course):
    """the trial's modules when setup is not told: the first module and the course's cheapest module with practical work
    - a simulator exercise before real equipment - so every trial builds the paper exercises, the activity screens and
    the classroom files; with no practical work in the course, the first and the middle module. Two modules: a practical
    module takes a theory module's place, the trial costs no more"""
    plan = [m for m in (load(workspace.claude_path(course, "plan.json"), {}) or {}).get("modules") or []
            if isinstance(m, dict) and str(m.get("module")).isdigit()]
    minutes = {int(m["module"]): float(m.get("built_min") or 0) for m in plan}
    if not minutes:                       # no Stage 2 plan yet: a module per programme topic
        prog = load(workspace.claude_path(course, "programme.json"), {}) or {}
        topics = prog.get("topics") if isinstance(prog.get("topics"), dict) else {}
        hour = float(prog.get("academic_hour_min") or 45)
        minutes = {int(k): hour * sum(float(t.get(x) or 0) for x in ("theory", "practical")) for k, t in topics.items()
                   if str(k).isdigit() and isinstance(t, dict) and not t.get("assessment")}
    work = sim_cov().practical(course)["modules"]
    nums = sorted(minutes) or sorted(work)
    if not nums:
        return list(DEFAULT_MODULES)
    first = nums[0]
    pick = sorted((n for n in work if n != first), key=lambda n: (RANK.get(work[n]["kind"], 9), minutes.get(n) or 1e9, n))
    if pick:
        return [first, pick[0]]
    return [first, nums[len(nums) // 2]] if len(nums) > 1 else [first]


def lane_note(course, modules):
    """a line when the trial's modules build no practical work and the course has some - None when they do, or it has none"""
    work = sim_cov().practical(course)["modules"]
    real = [n for n, r in work.items() if r["kind"] != "unnamed"]
    if not real or any(m in real for m in modules):
        return None
    return ("Modules %s have no simulator or equipment exercise, so this trial does not test the paper exercises - M%02d would "
            "(%s; sim_coverage.py practical)." % (", ".join(map(str, modules)), default_modules(course)[-1],
                                                 ", ".join("M%02d %s" % (n, work[n]["kind"]) for n in real)))


def setup(home, source, modules):
    """-> (config, problems)"""
    master, course = master_and_course(source)
    inputs = {"source_files": os.path.join(master, "source_files"), "old_course": os.path.join(master, "old_course")}
    probs = ["%s: not found - a trial needs the course's %s" % (p, k) for k, p in inputs.items() if not os.path.isdir(p)]
    intake = os.path.join(course, "working_claude", "intake.json")
    if not os.path.isfile(intake):
        probs.append("%s: not found - a trial reuses the course's decisions (its intake)" % intake)
    if probs:
        return None, probs
    os.makedirs(os.path.join(home, "decisions"), exist_ok=True)
    for name in DECISIONS:
        src = os.path.join(course, "working_claude", name)
        if os.path.isfile(src):
            data = load(src, {})
            if name == "intake.json" and isinstance(data, dict):
                data["course_name"] = TITLE
                for a in data.get("asked") or []:
                    if "course name" in str(a.get("question", "")).lower():
                        a["answer"] = TITLE
            save(os.path.join(home, "decisions", name), data)
    kb = ((load(intake, {}) or {}).get("knowledge_base") or {}).get("path")
    cfg = {"from": master, "inputs": dict(inputs, knowledge_base=kb or ""), "modules": modules,
           "made": datetime.now().strftime("%Y-%m-%d %H:%M")}
    save(os.path.join(home, "trial.json"), cfg)
    return cfg, []


def link(target, at):
    """a folder linked, never copied: a junction on Windows (no rights needed), a symlink elsewhere"""
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", at, target], capture_output=True, text=True)
        if r.returncode != 0:
            raise OSError("could not link %s: %s" % (target, (r.stderr or r.stdout).strip()))
    else:
        os.symlink(target, at, target_is_directory=True)


def is_link(p):
    return os.path.islink(p) or (hasattr(os.path, "isjunction") and os.path.isjunction(p))


def remove_run(master):
    """the last trial course gone - only a folder with the marker; links are taken away as links first, so what they
    point to (the real source_files and old course) is never touched"""
    if not os.path.isdir(master):
        return
    if not os.path.isfile(os.path.join(master, MARKER)):
        raise OSError("%s has no %s - not a trial folder, nothing deleted" % (master, MARKER))
    for name in os.listdir(master):
        p = os.path.join(master, name)
        if is_link(p):
            try:
                os.unlink(p)
            except OSError:
                os.rmdir(p)
    shutil.rmtree(master)


# ------------------------------------------------------------------ the stages a trial may reuse
# What each stage reads of the factory, in one place - paths under the plugin folder. A folder counts every file in it but
# the tests; "file#Heading" counts one section of a guide, from its "## Heading" to the next "## " ("file#": the part before
# the first). Left out on purpose, as none decides what a stage writes: the words of the pages (knowledge/page-labels.json),
# the laws' reasoning (references/), the builder's part lists (kit CATALOGUE.md, kit3d PARTS.md), and for Stage 1-2 two
# modules its scripts import only as helpers - content_script.py to read a script, compile's additional_materials.py to
# write a Word file - the gate check on the copied files judges what Stage 1-2 left.
CF = "skills/course-factory/"
SKILL_MD = CF + "SKILL.md#"
STAGES = {
    "read": [SKILL_MD] + [SKILL_MD + h for h in ("Every reply", "The operator's request wins", "Owner decisions in force",
                                                "The course remembers", "Mode first", "The brief", "The gate")]
            + [CF + "knowledge/" + k for k in ("intake.json", "course-type.json", "bloom.json", "active-learning.json",
                                               "media-and-tasks.json", "theory-rules.json", "instructor-led.json")]
            + [CF + d for d in ("hours/GUIDE.md", "hours/knowledge/", "hours/scripts/check_hours.py", "coverage/", "kb/",
                                "bloom/GUIDE.md", "active/GUIDE.md", "instructor-led/GUIDE.md", "templates/")]
            + [CF + "scripts/" + s for s in ("workspace.py", "old_course.py", "ilo_map.py", "make_architecture_page.py",
                                            "pedagogy_review.py", "course_gate.py", "active_plan.py",
                                            "bloom_map.py", "course_memory.py", "instructor_led.py")]
            + ["skills/course-visuals/scripts/subject_library.py"],
    "script": [SKILL_MD + h for h in ("Owner decisions in force", "Stage 3", "Auto build")]
              + [CF + "script/", CF + "kb/scripts/kb_tool.py"]
              + [CF + "knowledge/" + k for k in ("theory-rules.json", "media-and-tasks.json", "slide-text-rules.json",
                                                 "design-rules.json", "classroom-system.json", "active-learning.json", "bloom.json")]
              + [CF + "scripts/" + s for s in ("content_script.py", "fact_check.py", "task_cover.py", "figure_why.py",
                                              "check_slide_text.py", "design_choices.py", "interact_formats.py", "ilo_map.py",
                                              "bloom_map.py", "old_course.py", "course_gate.py", "workspace.py")]
              + ["skills/course-module-ui/knowledge/layout-templates.json", "skills/course-visuals/SKILL.md",
                 "agents/fact-checker.md", "agents/task-coverage-checker.md"],
}
STAGE_NAMES = {"read": "Stage 1-2 (intake, programme, architecture, ILO map, pedagogy review)",
               "script": "the content scripts (written, task-covered, fact-checked, approved)"}
# what each stage leaves in the course folder (paths under course\); MNN is the module's. A missing one is not copied
OUTPUTS = {
    "read": ["to_review/ARCHITECTURE_REVIEW.html", "to_review/pedagogy/"]
            + ["working_claude/" + f for f in ("architecture.json", "ilo_map.json", "programme.json", "plan.json",
                                                "pedagogy_review.json", "old_course_inventory.json", "OLD_COURSE_INVENTORY.md",
                                                "old_course_images/", "intake.json", "kb_sources.json", "STANDARDS.md",
                                                "reader_report.md", "instructor_led.json", "simulators.json",
                                                "model_course_syllabus.json")],
    "script": ["working_claude/script/MNN.json", "working_claude/fact_check/MNN.json", "working_claude/fact_check/MNN.changes.json",
               "working_claude/task_cover/MNN.json", "working_claude/task_cover/MNN.changes.json",
               "to_review/MNN_SCRIPT.docx", "to_review/MNN_SCRIPT_REVIEW.html", "to_review/MNN_INSTRUCTOR_NOTES.md"],
}
REFRESHED = ("where_taught", "checked_by", "taught_on", "checked_on")      # the ILO map's columns ilo_map.py refresh writes
REUSE = "reuse"                                                           # <home>\reuse\: the last trial's stages, kept


def git(cwd, *args):
    """git's output as bytes, or None (no git, not a repository, a failed command)"""
    try:
        r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True)
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


class OnDisk(object):
    """the plugin's files as they are now"""

    def __init__(self, plugin_dir):
        self.root = os.path.abspath(plugin_dir)

    def read(self, rel):
        try:
            return io.open(os.path.join(self.root, rel), "rb").read()
        except OSError:
            return None

    def files(self, rel):
        top = os.path.join(self.root, rel)
        return sorted(os.path.relpath(os.path.join(r, f), self.root).replace("\\", "/")
                      for r, _, fs in os.walk(top) for f in fs)


class AtCommit(object):
    """the plugin's files as one commit of its repository holds them"""

    def __init__(self, plugin_dir, commit):
        self.dir, self.commit = os.path.abspath(plugin_dir), commit
        self.prefix = (git(self.dir, "rev-parse", "--show-prefix") or b"").decode("utf-8").strip()
        self.cat = None

    def read(self, rel):
        """one file at the commit, through one git cat-file --batch for all of them"""
        if self.cat is None:
            self.cat = subprocess.Popen(["git", "-C", self.dir, "cat-file", "--batch"], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.cat.stdin.write(("%s:%s%s\n" % (self.commit, self.prefix, rel)).encode("utf-8"))
        self.cat.stdin.flush()
        head = self.cat.stdout.readline().split()
        if len(head) != 3 or head[1] != b"blob":
            return None
        data = self.cat.stdout.read(int(head[2]))
        self.cat.stdout.read(1)
        return data

    def close(self):
        if self.cat:
            self.cat.stdin.close()
            self.cat.wait()
            self.cat = None

    def files(self, rel):
        out = git(self.dir, "ls-tree", "-r", "--name-only", "--full-tree", self.commit, "--", self.prefix + rel.rstrip("/"))
        n = len(self.prefix)
        return sorted(x[n:] for x in (out or b"").decode("utf-8").splitlines() if x)


def section(text, heading):
    """one "## " section of a guide, its heading line included; heading "" - the part before the first; None: not there"""
    lines = text.split("\n")
    if not heading:
        return "\n".join(lines[:next((i for i, x in enumerate(lines) if x.startswith("## ")), len(lines))])
    start = next((i for i, x in enumerate(lines) if x.startswith("## " + heading)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def counted(rel):
    """a file a stage reads - not a test, its fixtures or a compiled copy"""
    parts = rel.split("/")
    return not (parts[-1].startswith("test_") or parts[-1].endswith(".pyc") or "__pycache__" in parts or "fixtures" in parts)


def digest(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()[:16] if data is not None else "missing"


def stage_hashes(src, stage):
    """{entry: hash} of every entry a stage reads, from src (OnDisk or AtCommit)"""
    out = {}
    for entry in STAGES[stage]:
        path, _, heading = entry.partition("#")
        if "#" in entry:
            data = src.read(path)
            part = section(data.replace(b"\r\n", b"\n").decode("utf-8", "replace"), heading) if data is not None else None
            out[entry] = digest(part.encode("utf-8")) if part is not None else "missing"
        elif entry.endswith("/"):
            files = [f for f in src.files(path) if counted(f)]
            out[entry] = hashlib.sha256("\n".join("%s %s" % (f[len(path):], digest(src.read(f))) for f in files)
                                        .encode("utf-8")).hexdigest()[:16] if files else "missing"
        else:
            out[entry] = digest(src.read(path))
    return out


def factory_record(plugin_dir=None):
    """what a trial records of the factory it ran: its commit and each stage's hashes"""
    d = plugin_dir or PLUGIN
    head = (git(d, "rev-parse", "HEAD") or b"").decode("utf-8").strip()
    return {"commit": head, "stages": {s: stage_hashes(OnDisk(d), s) for s in STAGES}}


def version_commit(plugin_dir, version):
    """(the one commit whose plugin.json first says this version, why) - (None, why) when none or several do"""
    prefix = (git(plugin_dir, "rev-parse", "--show-prefix") or b"").decode("utf-8").strip()
    log = git(plugin_dir, "log", "--format=%H", "--", ".claude-plugin/plugin.json")
    if log is None:
        return None, "the factory at %s is not a git checkout, so its version %s names no commit" % (plugin_dir, version)
    said = []
    for sha in log.decode("utf-8").split():
        try:
            if json.loads(git(plugin_dir, "show", "%s:%s.claude-plugin/plugin.json" % (sha, prefix)) or b"{}").get("version") == version:
                said.append(sha)
        except ValueError:
            continue
    if len(said) != 1:
        return None, "version %s names %s commit(s) of the factory, not one" % (version, len(said))
    return said[0], "matched by its version %s to commit %s (that trial recorded no hashes)" % (version, said[0][:7])


def then_hashes(mark, stage, plugin_dir):
    """(the hashes of a stage as the earlier trial ran it, how they were found) - (None, why) when they cannot be known"""
    rec = ((mark.get("factory") or {}).get("stages") or {}).get(stage)
    if rec:
        return rec, "by the hashes it recorded"
    commit = (mark.get("factory") or {}).get("commit")
    why = "by its commit %s" % commit[:7] if commit else ""
    if not commit:
        commit, why = version_commit(plugin_dir, mark.get("plugin", "?"))
        if not commit:
            return None, why
    if git(plugin_dir, "cat-file", "-e", commit + "^{commit}") is None:
        return None, "its commit %s is not in the factory's repository" % commit[:7]
    src = AtCommit(plugin_dir, commit)
    try:
        return stage_hashes(src, stage), why
    finally:
        src.close()


def previous_trial(path):
    """the trial course (master folder, its marker) an earlier trial left: a trial home, its run\\ or runs\\<run> folder, or
    the trial course itself; (None, why) when there is none - a home keeps only its last run's course"""
    path = os.path.abspath(path)
    run = os.path.basename(os.path.dirname(path)) == "runs"
    master = (os.path.join(os.path.dirname(os.path.dirname(path)), "run", TITLE) if run
              else path if os.path.isfile(os.path.join(path, MARKER)) else os.path.join(path, "run", TITLE))
    mark = load(os.path.join(master, MARKER))
    if not isinstance(mark, dict):
        return None, "%s holds no trial course (no %s)" % (path, MARKER)
    if run:
        try:
            ran = datetime.strptime(str(mark.get("started")), "%Y-%m-%d %H:%M").strftime("%Y%m%d-%H%M")
        except ValueError:
            ran = ""
        if not os.path.basename(path).startswith(ran or "-"):
            return None, "%s is not its home's last run (that started %s) - only the last run's course is kept" % (
                os.path.basename(path), mark.get("started"))
    return master, mark


def snapshot(master, mark, home):
    """the stages' files of a trial course kept in <home>\\reuse\\ - the course is deleted by the next run"""
    dest = os.path.join(home, REUSE)
    shutil.rmtree(dest, ignore_errors=True)
    course = os.path.join(master, "course")
    mids = [cs.mid(m) for m in mark.get("modules") or []]
    for rel in OUTPUTS["read"] + [x.replace("MNN", mid) for x in OUTPUTS["script"] for mid in mids]:
        src, to = os.path.join(course, rel), os.path.join(dest, "course", rel)
        if os.path.isdir(src):
            shutil.copytree(src, to)
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(to), exist_ok=True)
            shutil.copy2(src, to)
    save(os.path.join(dest, MARKER), dict(mark, kept_from=master))
    return dest


def decide(kept, modules, plugin_dir=None, fresh=False):
    """{stage: {"reuse": bool, "why": str, "changed": [...]}} for the stages an earlier trial left in kept (a folder holding
    its course\\ and marker: <home>\\reuse\\, or the trial course itself) - the script stage also {"modules": [...]}"""
    mark = load(os.path.join(kept, MARKER))
    out = {}
    for stage in STAGES:
        if fresh:
            out[stage] = {"reuse": False, "why": "--fresh: every stage runs"}
            continue
        if not isinstance(mark, dict):
            out[stage] = {"reuse": False, "why": "no earlier trial to take it from"}
            continue
        if stage == "script" and not out["read"]["reuse"]:
            out[stage] = {"reuse": False, "why": "the scripts are written against Stage 1-2, which runs"}
            continue
        then, how = then_hashes(mark, stage, plugin_dir or PLUGIN)
        trial = "the trial of course-factory %s, %s" % (mark.get("plugin", "?"), mark.get("started", "?"))
        if then is None:
            out[stage] = {"reuse": False, "why": "the factory files %s read when %s ran cannot be known: %s" % (stage, trial, how)}
            continue
        now = stage_hashes(OnDisk(plugin_dir or PLUGIN), stage)
        changed = [e for e in STAGES[stage] if then.get(e) != now.get(e)]
        if changed:
            out[stage] = {"reuse": False, "changed": changed, "why": "%d of the %d factory files and sections it reads changed "
                          "since %s (%s): %s" % (len(changed), len(now), trial, how, ", ".join(changed))}
            continue
        out[stage] = {"reuse": True, "from": mark.get("kept_from", ""), "why": "from %s - the %d factory files and sections it "
                      "reads are unchanged (%s)" % (trial, len(now), how)}
        if stage == "script":
            have = [m for m in modules if m in (mark.get("modules") or [])
                    and os.path.isfile(os.path.join(kept, "course", "working_claude", "script", cs.mid(m) + ".json"))]
            out[stage]["modules"] = have
            if not have:
                out[stage].update(reuse=False, why="the last trial scripted none of modules %s" % ", ".join(map(str, modules)))
    return out


CHECK_COPIED = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import course_gate, content_script as cs
course, mods = sys.argv[2], json.loads(sys.argv[3])
out = {"gate": course_gate.problems(course), "modules": {}}
for m in mods:
    s = cs.load(cs.paths(course, m)["script"])
    probs = cs.validate(s)
    if not (s.get("status") == "approved" and s.get("approved_hash") == cs.content_hash(s)):
        probs.append("not approved as it is")
    if not probs:
        probs = ["%s: %s" % (f["where"], f["detail"]) for f in cs.approval_blockers(course, s)[0]]
    out["modules"][str(m)] = probs
print(json.dumps(out))
"""


def check_copied(course, modules, plugin_dir=None):
    """the copied stages judged by the factory that will build: {"gate": [problems], "modules": {"1": [problems]}}"""
    scripts = os.path.join(plugin_dir or PLUGIN, "skills", "course-factory", "scripts")
    r = subprocess.run([sys.executable, "-c", CHECK_COPIED, scripts, course, json.dumps(modules)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"gate": ["the check of the copied files did not run: %s" % (r.stderr.strip().splitlines() or ["?"])[-1]], "modules": {}}


def reuse_into(kept, course, plan, plugin_dir=None):
    """copy the stages the plan reuses from kept into the new trial course and judge them with this factory; a stage that
    fails is taken out again and runs. Changes plan in place"""
    kept = os.path.join(kept, "course")
    copied = {"read": [], "script": {}}

    def put(rel):
        """(the path, what was there before - a decision file the run already has) or None when there is nothing to copy"""
        src, to = os.path.join(kept, rel), os.path.join(course, rel)
        was = io.open(to, "rb").read() if os.path.isfile(to) else None
        if os.path.isdir(src):
            shutil.rmtree(to, ignore_errors=True)
            shutil.copytree(src, to)
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(to), exist_ok=True)
            shutil.copy2(src, to)
        else:
            return None
        return to, was

    def take_out(paths):
        for p, was in paths:
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif was is not None:
                io.open(p, "wb").write(was)
            elif os.path.isfile(p):
                os.remove(p)

    if not plan["read"]["reuse"]:
        return plan
    copied["read"] = [p for p in map(put, OUTPUTS["read"]) if p]
    mods = plan["script"].get("modules", []) if plan["script"]["reuse"] else []
    for m in mods:
        copied["script"][m] = [p for p in (put(x.replace("MNN", cs.mid(m))) for x in OUTPUTS["script"]) if p]
    ilo = os.path.join(course, "working_claude", "ilo_map.json")
    m = load(ilo)
    if isinstance(m, dict):                    # the slide and question columns of a module whose script is not reused
        keep = {cs.mid(x) for x in mods}
        for row in m.get("rows") or []:
            if isinstance(row, dict) and str(row.get("module")) not in keep:
                for k in REFRESHED:
                    row.pop(k, None)
        save(ilo, m)
    said = check_copied(course, mods, plugin_dir)
    if said["gate"]:
        take_out(copied["read"] + [p for ps in copied["script"].values() for p in ps])
        plan["read"].update(reuse=False, why="taken from the last trial, the copy does not pass the gate with this factory: "
                            + " / ".join(said["gate"]))
        plan["script"] = {"reuse": False, "why": "the scripts are written against Stage 1-2, which runs"}
        return plan
    left = []
    for x in mods:
        probs = said["modules"].get(str(x), ["not judged"])
        if probs:
            take_out(copied["script"][x])
            plan["script"].setdefault("not", {})[x] = "not approvable with this factory: " + " / ".join(probs[:5])
        else:
            left.append(x)
    if mods:
        plan["script"]["modules"] = left
    if mods and not left:
        plan["script"].update(reuse=False, why="no copied script is approvable with this factory: " + "; ".join(
            "M%02d %s" % (k, v) for k, v in plan["script"].get("not", {}).items()))
    memory = os.path.join(plugin_dir or PLUGIN, "skills", "course-factory", "scripts", "course_memory.py")
    subprocess.run([sys.executable, memory, "start", course, "--title", TITLE], capture_output=True)
    return plan


def flow_prompt(full=False):
    """the prompt's lines on how far the run goes: the first pass alone, or the full build with its fix round"""
    return FULL_RUN if full else FIRST_PASS


def stages_prompt(plan, modules):
    """the prompt's lines on what this run does of Stage 1-3"""
    mods = ", ".join(str(m) for m in modules)
    if not plan or not plan["read"]["reuse"]:
        return FRESH.format(modules=mods)
    done = plan["script"].get("modules", []) if plan["script"]["reuse"] else []
    out = [READ_REUSED.format(why=plan["read"]["why"])]
    if done:
        out.append(SCRIPTS_REUSED.format(done=", ".join(map(str, done))))
    todo = [m for m in modules if m not in done]
    out.append(SCRIPTS_TO_WRITE.format(modules=", ".join(map(str, todo))) if todo else "- Leave every other module unscripted.")
    return "\n".join(out)


def reuse_lines(plan):
    """the plan in words, one line a stage"""
    out = []
    for stage in STAGES:
        p = (plan or {}).get(stage)
        if not p:
            continue
        what = STAGE_NAMES[stage]
        if p["reuse"] and stage == "script":
            what += " of modules %s" % ", ".join(map(str, p.get("modules", [])))
        out.append("  %s %s - %s" % ("REUSED" if p["reuse"] else "RUNS  ", what, p["why"]))
        out += ["         module %s runs: %s" % (k, v) for k, v in sorted((p.get("not") or {}).items())]
    return out


def prepare_run(home, cfg, modules, plugin_dir=None, fresh=False, full=False):
    """the new trial course: -> (master folder, run folder, prompt). The last run's stages are kept first (snapshot), then
    taken where nothing they depend on changed (decide, reuse_into)"""
    master = os.path.join(home, "run", TITLE)
    last = load(os.path.join(master, MARKER))
    if isinstance(last, dict):
        snapshot(master, last, home)
    remove_run(master)
    course = os.path.join(master, "course")
    os.makedirs(os.path.join(course, "working_claude"))
    mark = {"trial": True, "modules": modules, "from": cfg["from"], "plugin": plugin_version(plugin_dir),
            "started": datetime.now().strftime("%Y-%m-%d %H:%M"), "factory": factory_record(plugin_dir), "first_pass": not full}
    save(os.path.join(master, MARKER), mark)
    for name in ("source_files", "old_course"):
        link(cfg["inputs"][name], os.path.join(master, name))
    for name in DECISIONS:
        src = os.path.join(home, "decisions", name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(course, "working_claude", name))
    kept = os.path.join(home, REUSE)
    plan = reuse_into(kept, course, decide(kept, modules, plugin_dir, fresh), plugin_dir)
    mark["reused"] = plan
    save(os.path.join(master, MARKER), mark)
    run_dir = os.path.join(home, "runs", datetime.now().strftime("%Y%m%d-%H%M") + "_" + plugin_version(plugin_dir))
    os.makedirs(run_dir, exist_ok=True)
    prompt = TRIAL_PROMPT.format(stages=stages_prompt(plan, modules), flow=flow_prompt(full))
    io.open(os.path.join(run_dir, "prompt.txt"), "w", encoding="utf-8").write(prompt)
    return master, run_dir, prompt


def claude_command(prompt, plugin_dir=None):
    """claude -p as an event stream, so the log is written as the run goes, not only at its end"""
    cmd = course_portal.claude_command(prompt) + course_portal.STREAM
    return cmd + (["--plugin-dir", os.path.abspath(plugin_dir)] if plugin_dir else [])


# the log as the run goes, and a run that ends on Claude's usage limit - the same for the auto build (course_portal.py)
readable, stopped_by = course_portal.readable, course_portal.stopped_by


def run_claude(cmd, cwd, env, logf, hours=20):
    """claude -p in the trial course, each line of its stream written to the log as it comes, carried on in the same
    session when it ends without its last line (course_portal.run_print); -> its exit code"""
    try:
        return course_portal.run_print(cmd, cwd, env, logf, r"TRIAL (DONE|STOPPED)", hours)
    except subprocess.TimeoutExpired:
        io.open(logf, "a", encoding="utf-8").write("TRIAL STOPPED: still running after %d hours\n" % hours)
        return 1


# ------------------------------------------------------------------ the scorecard
COMPILE = os.path.join(os.path.dirname(HERE), "compile", "scripts")
FIT_SIZES = ("1280x800", "1024x768")
WORDS_OVER = 120
VERDICT = re.compile(r"^(PASS|FAIL|MODULE CLEAN|PHASE A CLEAN|STILL RUNNING)\b")
PICTURE_TAGS = ("img", "svg", "canvas", "video", "iframe", "object")
PICTURE_ATTRS = ("data-kit3d", "data-3d", "data-kit2d")      # a 3D scene, a 2D-kit figure: drawn when the page opens


def module_dir(course, m):
    return os.path.join(course, workspace.MODULES, "module%02d" % m)


def measured(fn, *args):
    """fn's answer, or None when it could not be measured - one number never stops the scorecard"""
    try:
        return fn(*args)
    except Exception:  # noqa: BLE001
        return None


CUT_KINDS = ("cut", "spill", "picture", "figure")      # fit_gate.py's findings of something shown in part


def fit_slides(deck, no_browser):
    """{size: slides with words cut or a picture cropped at that size, every Next pressed} - fit_gate.py at the tablets'
    1280 x 800 and at 1024 x 768; {} when nothing could be measured. Only what is cut or cropped counts: the gate's other
    findings (a drawing that never changes, lines walked twice) are not a cut slide"""
    if no_browser or not os.path.isfile(deck):
        return {}
    sys.path.insert(0, os.path.join(PLUGIN, "skills", "course-module-ux", "measure", "scripts"))
    import contextlib
    import tempfile
    import fit_gate
    out = os.path.join(tempfile.mkdtemp(prefix="trial_fit_"), "fit.json")
    args = [deck] + [x for size in FIT_SIZES for x in ("--viewport", size)] + ["--json", out]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            code = fit_gate.main(args)
        found = load(out) if code in (0, 1) else None
    finally:
        shutil.rmtree(os.path.dirname(out), ignore_errors=True)
    if not isinstance(found, dict):
        return {}
    return {size: len({x[0] for x in found.get(size) or [] if x[2] in CUT_KINDS}) for size in FIT_SIZES if size in found}


def build_verdict(course, mid):
    """(the last build's verdict line, passed) from its answer file: PASS or MODULE CLEAN passed, FAIL or PHASE A CLEAN did
    not; ("", None) when no build answered"""
    ans = os.path.join(course, "working_claude", "_build", "%s_answer.txt" % mid)
    if not os.path.isfile(ans):
        return "", None
    lines = [x.strip() for x in io.open(ans, encoding="utf-8", errors="replace").read().splitlines() if x.strip()]
    said = [x for x in lines if VERDICT.match(x)]
    if not said:
        return ([x for x in lines if not x.startswith("Full log")] or [""])[-1], None
    return said[-1], said[-1].startswith(("PASS", "MODULE CLEAN"))


def build_minutes(course, mid):
    """minutes from the module's starter build sheet to its first PASS, as the build's clock kept them (cf_timing.py)"""
    rec = load(os.path.join(course, "working_claude", "_build", "%s_clock.json" % mid)) or {}
    return rec.get("minutes") if rec.get("passed") else None


class DeckScan(HTMLParser):
    """each slide of a built deck: its template and variant, its pictures and the placeholders among them, and the words the
    room sees at once - its words outside its parts and its longest part (content-in-parts shows one part at a time). The
    header band, the source line, the controls, the words inside a drawing and the compiler's own words (a step's number, an
    answer shown a second time over the figure: data-script-ignore) are not counted (check_script_match.py)"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        import check_script_match as csm
        import compile_module as cm
        self.exempt_tags, self.exempt_classes, self.void = csm.EXEMPT_TAGS, csm.EXEMPT_CLASSES, csm.VOID
        self.placeholder = cm.PLACEHOLDER_IMG
        self.stack, self.slides = [], []      # stack: (tag, its words not counted, part, a slide)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        cls = set(a.get("class", "").split())
        slide = tag == "section" and "slide" in cls
        if slide:
            self.slides.append({"id": a.get("id", ""), "template": a.get("data-template", ""), "variant": a.get("data-variant", ""),
                                "pictures": 0, "placeholders": 0, "words": 0, "parts": {}})
        inside = any(x[3] for x in self.stack) or slide
        if inside and not any(x[0] == "button" for x in self.stack) and (tag in PICTURE_TAGS or any(k in a for k in PICTURE_ATTRS)):
            self.slides[-1]["pictures"] += 1
            if self.placeholder.search(a.get("src", "")):
                self.slides[-1]["placeholders"] += 1
        if tag not in self.void:
            self.stack.append((tag, tag in self.exempt_tags or bool(cls & self.exempt_classes) or "data-script-ignore" in a,
                               a.get("data-part") if "lt-part" in cls else None, slide))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if not any(x[3] for x in self.stack) or any(x[1] for x in self.stack):
            return
        s = self.slides[-1]
        part = next((x[2] for x in reversed(self.stack) if x[2] is not None), None)
        if part is None:
            s["words"] += cs.wc(data)
        else:
            s["parts"][part] = s["parts"].get(part, 0) + cs.wc(data)


def scan_deck(deck):
    if COMPILE not in sys.path:
        sys.path.append(COMPILE)
    p = DeckScan()
    p.feed(io.open(deck, encoding="utf-8", errors="replace").read())
    for s in p.slides:
        s["seen_words"] = s["words"] + max(s["parts"].values(), default=0)
    return p.slides


def off_blueprint(slides):
    """the slides off their blueprint, judged as the build's course package check judges them
    (check_course_package.off_blueprint): an unknown template, version or variant, or a picture slot empty or a placeholder"""
    import check_course_package as ccp
    return ccp.off_blueprint(slides)


def pictures_pending(course, m, slides):
    """the screens whose picture is still Phase A's stand-in: the build sheet's (build_module.phase_a_slots) and any slide of
    the deck that shows a placeholder"""
    if COMPILE not in sys.path:
        sys.path.append(COMPILE)
    import build_module
    return len({sid for sid, _ in build_module.phase_a_slots(course, m)} | {s["id"] for s in slides or [] if s["placeholders"]})


def three_d_share(deck):
    """% of the teaching slides with interactive 3D, counted as the course package counts it for L67"""
    import check_course_package as ccp
    three, teach = ccp.three_d_share(ccp.parse(deck).slides)
    return int(round(100.0 * len(three) / len(teach))) if teach else None


def perf_slides(deck, no_browser):
    """slides whose 3D lags at 1280 x 800, CPU slowed 4x (perf_gate.py) - None when not measured"""
    if no_browser or not os.path.isfile(deck):
        return None
    sys.path.insert(0, os.path.join(PLUGIN, "skills", "course-module-ux", "measure", "scripts"))
    import contextlib
    import perf_gate
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = perf_gate.main([deck])
    m = re.search(r"FAIL (\d+) slide", buf.getvalue())
    return int(m.group(1)) if m else (0 if code == 0 else None)


FINDING_KINDS = (("overflow_cut", "overflow/cut"), ("blueprint", "blueprint"), ("three_d", "3D"), ("words", "words"),
                 ("task_pages", "task pages"), ("script", "script"), ("figures", "figures"), ("other", "other"))


def first_pass_row(course, m):
    """the first-pass lines of one module: the script's rounds (working_claude/first_pass.json, written by the run) and what the
    first build and its one review found (the build workflow's result.json); nothing of either in a full trial"""
    row = {}
    script = (((load(workspace.claude_path(course, "first_pass.json")) or {}).get("scripts") or {}).get(str(m)) or {})
    if script:
        row["script_rewrite_rounds"] = script.get("rewrite_rounds")
        row["must_fixes_first_check"] = script.get("must_fixes_first_check")
        row["script_approved_first_pass"] = "yes" if script.get("approved_clean") else "no - open: %s" % (
            "; ".join(script.get("open_must_fixes") or []) or "not recorded")[:160]
    result = load(os.path.join(workspace.claude_path(course, "_build"), "agents", "result.json")) or {}
    build = next((x for x in ((result.get("first_pass") or {}).get("modules") or []) if str(x.get("module")) == str(m)), None)
    if build:
        row["builds_used"] = build.get("builds")
        row["first_build_verdict"] = str(build.get("first_build") or "")[:90]
        kinds = build.get("findings") or {}
        row["first_review_findings"] = ", ".join("%s %d" % (name, kinds[k]) for k, name in FINDING_KINDS if kinds.get(k)) or "none"
        row["first_review_findings_total"] = build.get("findings_total")
    if script or build:
        row["first_pass_clean"] = "yes" if (build and build.get("clean") and script.get("approved_clean", True)
                                            and not script.get("rewrite_rounds")) else "no"
    return row


def score_module(course, m, no_browser=False):
    mid = cs.mid(m)
    row = {"module": m}
    sp = cs.paths(course, m)["script"]
    script = cs.load(sp) if os.path.isfile(sp) else None
    deck = os.path.join(module_dir(course, m), "presentation", "index.html")
    row["built"] = os.path.isfile(deck)
    row["build_says"], row["passed"] = measured(build_verdict, course, mid) or ("", None)
    row["build_says"] = row["build_says"][:90]
    row["build_minutes"] = measured(build_minutes, course, mid)
    fit = measured(fit_slides, deck, no_browser) or {}
    row["cut_or_cropped_slides"], row["cut_at_1024x768"] = fit.get("1280x800"), fit.get("1024x768")
    row["slides_3d_lagging"] = measured(perf_slides, deck, no_browser)
    slides = measured(scan_deck, deck) if row["built"] else None
    off = measured(off_blueprint, slides) if slides else None
    row["off_blueprint_slides"] = None if off is None else len(off)
    row["pictures_pending"] = measured(pictures_pending, course, m, slides)
    row["interactive_3d_share"] = measured(three_d_share, deck) if row["built"] else None
    row["max_words_slide"] = max(s["seen_words"] for s in slides) if slides else None
    row["slides_over_120_words"] = sum(1 for s in slides if s["seen_words"] > WORDS_OVER) if slides else None
    if script:
        import fact_check
        if fact_check.course_kbs(course):
            st = fact_check.status(course, m, script)
            row["claims"], row["claims_unproven"], row["claims_unchecked"] = st["claims"], len(st["unproven"]), len(st["unchecked"])
        old = cs.old_course_findings(course, script)
        for rule in ("o_moved", "o_dropped", "o_thinner"):
            row[rule.replace("o_", "old_")] = sum(1 for f in old if f["rule"] == rule)
        found = measured(cs.all_findings, script, course)
        row["must_fix_left"] = None if found is None else len(cs.blocking(found))
        row["self_check_basic_tasks"] = measured(lambda: [cs.sc_mix(st["questions"])[0] for st in cs.plan_of(script)[1]
                                                          if st["kind"] == "self-check"])
        row["self_checks_off_mix"] = None if found is None else len({f["screen"] for f in found if f["rule"] == "t_sc_mix"})
    row.update(first_pass_row(course, m))
    rev = load(workspace.claude_path(course, "pedagogy_review.json"), {}) or {}
    rows = ((rev.get("modules") or {}).get(str(m)) or {}).get("rows") or {}
    row["bloom_lifts_over_one"] = sum(1 for x in rows.values() if isinstance((x.get("now") or {}).get("level"), int)
                                      and isinstance((x.get("proposed") or {}).get("level"), int)
                                      and (x["now"]["level"] or 0) >= 1 and x["proposed"]["level"] - x["now"]["level"] > 1
                                      and not (x.get("proposed") or {}).get("expert"))
    if row["built"]:
        page = io.open(deck, encoding="utf-8").read()
        tpl = re.findall(r'data-template="([\w-]+)', page)
        run = best = 0
        for i, t in enumerate(tpl):
            run = run + 1 if i and t == tpl[i - 1] else 1
            best = max(best, run)
        row["templates"], row["same_template_in_a_row"] = len(set(tpl)), best
        row.update(layout_plan.stats(*layout_plan.deck_shapes(page)))     # look_shapes, same_look_in_a_row, beside_share
    sim = os.path.join(course, "additional-materials", "simulator-and-equipment")
    row["practical_kind"] = ((measured(sim_cov().practical, course) or {}).get("modules", {}).get(m) or {}).get("kind") or "none"
    row["simulator_exercises"] = sum(1 for _, _, fs in os.walk(sim) for f in fs if re.match(r"%s_A\d+.*_TRAINEE\.pdf$" % mid, f))
    row["simulator_drafts_pending"] = measured(lambda: sum(1 for p in sim_pending(course) if p["module"] == m))
    return row


def sim_pending(course):
    """the drafted simulator tasks the course director has not accepted (L66, sim_coverage.py) - their minutes sit on a
    screen with no exercise behind it"""
    return sim_cov().pending(course)


LOWER_IS_BETTER = ("cut_or_cropped_slides", "cut_at_1024x768", "slides_3d_lagging", "claims_unproven", "claims_unchecked", "old_moved", "old_dropped",
                   "old_thinner", "must_fix_left", "bloom_lifts_over_one", "same_template_in_a_row", "same_look_in_a_row",
                   "beside_share", "build_minutes", "script_rewrite_rounds", "must_fixes_first_check", "builds_used", "first_review_findings_total",
                   "off_blueprint_slides", "pictures_pending", "max_words_slide", "slides_over_120_words", "self_checks_off_mix",
                   "simulator_drafts_pending")
# a number that is best inside a band: closer to it is better (L67: 60-80 % of the teaching slides with interactive 3D)
BANDS = {"interactive_3d_share": (int(round(100 * cs.MEDIA["three_d"]["min_share"])), int(round(100 * cs.MEDIA["three_d"]["max_share"])))}
SHOWN = ("built", "passed", "build_says", "build_minutes", "cut_or_cropped_slides", "cut_at_1024x768", "slides_3d_lagging", "off_blueprint_slides",
         "pictures_pending", "interactive_3d_share", "max_words_slide", "slides_over_120_words", "claims", "claims_unproven",
         "claims_unchecked", "old_moved", "old_dropped", "old_thinner", "must_fix_left", "bloom_lifts_over_one", "templates",
         "same_template_in_a_row", "look_shapes", "same_look_in_a_row", "beside_share", "self_check_basic_tasks", "self_checks_off_mix",
         "practical_kind", "simulator_exercises", "simulator_drafts_pending", "script_rewrite_rounds", "must_fixes_first_check",
         "script_approved_first_pass", "builds_used", "first_build_verdict", "first_review_findings", "first_review_findings_total",
         "first_pass_clean")


def compare(now, before):
    """[(module, metric, before, now, better or worse)] for every number that moved - a yes/no counts as 1/0, higher better;
    a number with a band is better closer to it ("-" when both are inside)"""
    out = []
    old = {r["module"]: r for r in (before or {}).get("modules", [])}
    for r in now.get("modules", []):
        b = old.get(r["module"]) or {}
        for k, v in r.items():
            if k == "module" or not isinstance(v, (int, float)) or not isinstance(b.get(k), (int, float)) or b.get(k) == v:
                continue
            if k in BANDS:
                lo, hi = BANDS[k]
                off = lambda x: max(lo - x, 0, x - hi)
                how = "-" if off(v) == off(b[k]) else "better" if off(v) < off(b[k]) else "worse"
            else:
                how = "better" if (v < b[k]) == (k in LOWER_IS_BETTER) else "worse"
            out.append((r["module"], k, b[k], v, how))
    return out


def shown(v):
    if v is None:
        return "-"
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) or "none"
    return str(v)


def show(card, before=None):
    """the scorecard module by module, beside the one before when there is one, then what moved; -> exit code (1 when a
    number got worse)"""
    print("FACTORY TRIAL - course-factory %s, started %s" % (card.get("plugin"), card.get("started")))
    stop = card.get("stopped")
    if stop:
        print("STOPPED: %s - the run ended before the factory finished; a module that did not pass is unfinished, not failed" % stop)
    if card.get("reused"):
        print("Taken from the last trial, or run again:\n" + "\n".join(reuse_lines(card["reused"])))
    if card.get("practical"):
        print("Practical work in the course:\n" + "\n".join("  " + x for x in card["practical"]))
    old = {r["module"]: r for r in (before or {}).get("modules", [])}
    if before:
        print("  %-24s %-16s %s" % ("", "before %s" % before.get("plugin"), "now %s" % card.get("plugin")))
    for r in card.get("modules", []):
        b = old.get(r["module"])
        print("\nModule %d%s" % (r["module"], " - stopped: %s, unfinished" % stop if stop and not r.get("passed") else ""))
        for k in SHOWN:
            if k not in r and k not in (b or {}):
                continue
            if before is None:
                print("  %-24s %s" % (k.replace("_", " "), shown(r.get(k))))
            elif isinstance(r.get(k), str) or isinstance((b or {}).get(k), str):
                print("  %-24s now:    %s\n  %-24s before: %s" % (k.replace("_", " "), shown(r.get(k)), "", shown((b or {}).get(k))))
            else:
                print("  %-24s %-16s %s" % (k.replace("_", " "), shown((b or {}).get(k)), shown(r.get(k))))
    moved = compare(card, before)
    if before:
        print("\nSince course-factory %s%s:" % (before.get("plugin"), " (this run stopped on its %s - a number that got worse may "
                                                                        "be work it never reached)" % stop if stop else ""))
        for m, k, b, v, how in moved or []:
            print("  M%02d %-24s %s -> %s  %s" % (m, k.replace("_", " "), b, v, how.upper() if how == "worse" else how))
        if not moved:
            print("  nothing moved")
    return 1 if any(x[4] == "worse" for x in moved) else 0


def course_to_score(folder):
    """(course folder, the trial's marker) of any trial course - its master folder or its course folder; a course with no
    marker is scored on every module it built"""
    folder = os.path.abspath(folder)
    course = os.path.join(folder, "course") if os.path.isdir(os.path.join(folder, "course")) else folder
    mark = load(os.path.join(os.path.dirname(course), MARKER)) or load(os.path.join(course, MARKER))
    if not mark:
        mods = os.path.join(course, workspace.MODULES)
        built = sorted(int(d[6:]) for d in (os.listdir(mods) if os.path.isdir(mods) else [])
                       if re.match(r"^module\d+$", d) and os.path.isfile(os.path.join(mods, d, "presentation", "index.html")))
        mark = {"plugin": "?", "started": "", "modules": built} if built else None
    return course, mark


def report(home, run_dir=None, no_browser=False, course=None, against=None):
    if course:
        course, mark = course_to_score(course)
        if not mark:
            print("No trial course to score in %s - no %s and no built module" % (course, MARKER))
            return 2
        runs = []
    else:
        cfg = load(os.path.join(home, "trial.json"))
        master = os.path.join(home, "run", TITLE)
        mark = load(os.path.join(master, MARKER))
        if not cfg or not mark:
            print("No trial course to score - setup, then run.")
            return 2
        course = os.path.join(master, "course")
        runs = sorted(d for d in os.listdir(os.path.join(home, "runs")) if os.path.isdir(os.path.join(home, "runs", d)))
        run_dir = run_dir or (os.path.join(home, "runs", runs[-1]) if runs else os.path.join(home, "runs", "report"))
    if against and not isinstance(load(against), dict):
        print("Stopped - %s is not a scorecard.json" % against)
        return 2
    card = {"plugin": mark.get("plugin"), "started": mark.get("started"), "scored": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "course": course, "modules": [score_module(course, m, no_browser) for m in mark.get("modules") or []]}
    if mark.get("reused"):
        card["reused"] = mark["reused"]
    card["practical"] = measured(lambda: sim_cov().practical_lines(sim_cov().practical(course)))
    logf = os.path.join(run_dir, "build.log") if run_dir else ""
    stop = stopped_by(io.open(logf, encoding="utf-8", errors="replace").read()) if os.path.isfile(logf) else None
    if stop:
        card["stopped"] = stop
    if run_dir:
        save(os.path.join(run_dir, "scorecard.json"), card)
    before = load(against) if against else None
    for d in reversed(runs if not against else []):
        p = os.path.join(home, "runs", d, "scorecard.json")
        if os.path.abspath(os.path.join(home, "runs", d)) != os.path.abspath(run_dir) and os.path.isfile(p):
            before = load(p)
            break
    code = show(card, before)
    print("\n    %s" % (os.path.join(run_dir, "scorecard.json") if run_dir else "not saved - --run <folder> keeps it"))
    return code


def setup_cmd(home, a):
    """setup, and setup --reuse <an earlier trial>: its inputs and modules unless --from / --modules say otherwise, and its
    Stage 1-3 kept for the next run (--dry-run: what that run would take, judged in a copy, and nothing written)"""
    master, mark = previous_trial(a.reuse) if a.reuse else (None, None)
    if a.reuse and not master:
        print("Stopped - " + mark)
        return 2
    earlier = (load(os.path.join(os.path.dirname(os.path.dirname(master)), "trial.json")) or {}) if master else {}
    source = a.source or earlier.get("from") or (mark or {}).get("from")
    mods = modules_of(a.modules or ",".join(map(str, earlier.get("modules") or (mark or {}).get("modules") or [])))
    if source and not mods and not a.modules:
        mods = default_modules(master_and_course(source)[1])
    if not source or not mods:
        print("Stopped - setup needs --from <the course's master folder> and --modules like 1,4,8,19")
        return 2
    if a.dry_run:
        if not master:
            print("Stopped - --dry-run shows what --reuse would take: name the earlier trial")
            return 2
        plan = decide(master, mods, a.plugin_dir)
        inputs = earlier.get("inputs") or {}
        if plan["read"]["reuse"]:
            tmp = os.path.join(tempfile.mkdtemp(prefix="trial_reuse_"), TITLE)
            course = os.path.join(tmp, "course")
            os.makedirs(os.path.join(course, "working_claude"))
            save(os.path.join(tmp, MARKER), {"trial": True, "dry_run": True})
            try:
                for name in ("source_files", "old_course"):
                    if os.path.isdir(inputs.get(name) or ""):
                        link(inputs[name], os.path.join(tmp, name))
                plan = reuse_into(master, course, plan, a.plugin_dir)
            finally:
                remove_run(tmp)
                shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
        print("A run of modules %s with course-factory %s would take from the trial of %s (%s), judged in a copy:\n%s\n"
              "Nothing written (--dry-run)." % (", ".join(map(str, mods)), plugin_version(a.plugin_dir), mark.get("plugin"),
                                                 mark.get("started"), "\n".join(reuse_lines(plan))))
        return 0
    cfg, probs = setup(home, source, mods)
    if probs:
        print("Stopped - " + "\n  ".join(probs))
        return 2
    if master:
        snapshot(master, mark, home)
        print("Kept for the next run - it would take:\n" + "\n".join(reuse_lines(decide(os.path.join(home, REUSE), mods, a.plugin_dir))))
    print("Trial ready in %s - modules %s, from %s. Run it after every major update: factory_trial.py run"
          % (home, ", ".join(map(str, mods)), cfg["from"]))
    note = lane_note(master_and_course(cfg["from"])[1], mods)
    if note:
        print("Note: " + note)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("setup", "run", "report", "compare", "status"))
    ap.add_argument("files", nargs="*")
    ap.add_argument("--home")
    ap.add_argument("--course")
    ap.add_argument("--against")
    ap.add_argument("--from", dest="source")
    ap.add_argument("--modules")
    ap.add_argument("--plugin-dir")
    ap.add_argument("--run")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--reuse")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--full", action="store_true", help="the full build with its fix round, not the first pass alone")
    a = ap.parse_args(argv)
    home = home_of(a.home)
    if a.cmd == "setup":
        return setup_cmd(home, a)
    cfg = load(os.path.join(home, "trial.json"))
    if a.cmd == "status":
        if not cfg:
            print("No trial yet - factory_trial.py setup --from <course master folder>")
            return 2
        runs = sorted(os.listdir(os.path.join(home, "runs"))) if os.path.isdir(os.path.join(home, "runs")) else []
        print("Trial from %s, modules %s; %d run(s)%s" % (cfg["from"], ", ".join(map(str, cfg["modules"])), len(runs),
                                                        ": " + ", ".join(runs[-5:]) if runs else ""))
        return 0
    if a.cmd == "report":
        return report(home, a.run, a.no_browser, a.course, a.against)
    if a.cmd == "compare":
        cards = [load(p) for p in a.files]
        if len(cards) != 2 or not all(isinstance(c, dict) for c in cards):
            print("Stopped - compare needs two scorecard.json files: the one before, then the one now")
            return 2
        return show(cards[1], cards[0])
    if not cfg:
        print("Stopped - no trial yet: factory_trial.py setup --from <course master folder>")
        return 2
    mods = modules_of(a.modules) if a.modules else cfg["modules"]
    if not mods:
        print("Stopped - --modules like 1,4")
        return 2
    try:
        master, run_dir, prompt = prepare_run(home, cfg, mods, a.plugin_dir, a.fresh, a.full)
    except OSError as err:
        print("Stopped - %s" % err)
        return 2
    cmd = claude_command(prompt, a.plugin_dir)
    note = lane_note(master_and_course(cfg["from"])[1], mods)
    if note:
        print("Note: " + note)
    print("\n".join(reuse_lines((load(os.path.join(master, MARKER)) or {}).get("reused"))))
    if a.dry_run:
        print("Trial course made in %s (modules %s). Not started (--dry-run) - it would run:\n  %s\n  in %s"
              % (master, ", ".join(map(str, mods)), " ".join(cmd[:2]) + " <the trial prompt> " + " ".join(cmd[3:6]) + " ...", master))
        return 0
    env = course_portal.unattended_env(NOVIKONTAS_AUTO_BUILD="1", NOVIKONTAS_TRIAL="1", **LIBRARIES_OFF)
    logf = os.path.join(run_dir, "build.log")
    print("Building the trial (modules %s) - this takes a while; the log, written as it goes: %s" % (", ".join(map(str, mods)), logf))
    rc = run_claude(cmd, master, env, logf)
    said = io.open(logf, encoding="utf-8", errors="replace").read()
    print("The build said: %s" % ([x for x in said.strip().splitlines() if x.strip()][-1:] or ["(nothing)"])[0][:200])
    code = report(home, run_dir)
    return code or (0 if rc == 0 and "TRIAL DONE" in said else 1)


if __name__ == "__main__":
    sys.exit(main())
