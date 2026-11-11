#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The factory trial - a few modules of a real course built from scratch after every major update, and scored.

    factory_trial.py setup  --from <course master folder> [--modules 1,4,8,19] [--home <folder>]
    factory_trial.py run    [--modules 1,4] [--plugin-dir <plugin folder>] [--dry-run] [--home <folder>]
    factory_trial.py report [--run <runs\\folder>] [--course <trial course>] [--against <scorecard.json>] [--no-browser] [--home <folder>]
    factory_trial.py compare <scorecard.json before> <scorecard.json now>
    factory_trial.py status [--home <folder>]

WHY THIS EXISTS
To see whether a release builds courses better, a whole course was built - hours of work, and every run asked other
questions and made other choices, so two runs could not be compared. The trial keeps one course's inputs (its
source_files, old course and knowledge base, read where they are) and its decisions (intake.json, kb_sources.json), and
builds only a few modules - the first, the ones with simulator exercises, one more - from an empty folder, unattended,
the way the office PC builds. Then it scores what was built and sets the score beside the last trial's.

  setup   remembers the course's inputs and copies its decision files (course name "FACTORY TRIAL"). Nothing is copied
          from the inputs: source_files and the old course are linked into each run (the factory only reads them, L14).
  run     deletes the last trial course - only a folder that carries FACTORY_TRIAL.json, and its links are removed as
          links, never their targets - makes a new one, and starts Claude Code in it (claude -p, the course-factory
          skill, its "Auto build" rules, NOVIKONTAS_TRIAL=1). Every STOP is signed "Factory trial"; the training app is
          never called; no paid picture is made; nothing is pushed. --plugin-dir builds with a plugin checkout instead of
          the installed one (a release before it is pushed); --modules builds only some of the trial's modules (a retest
          of two). The log and the score go to runs\\<date>\\ - the log line by line as the run goes (the session's words,
          each agent it starts, the minutes since the start and the cost so far). A run that ends without its last line
          and not on the usage limit is carried on in the same session (claude -p --resume), up to 3 times, in the same
          log. Then report.
  report  the scorecard of each trial module, and what changed since the last trial:
            built, passed (its last build said PASS or MODULE CLEAN) and that build's verdict; minutes to its first PASS
            (the build's clock, cf_timing.py); slides cut or pictures cropped at 1280 x 800 and at 1024 x 768, every Next
            pressed (fit_gate.py); slides off their blueprint - not a known template, version and variant
            (course-module-ui blueprints.json, layout-templates.json), or a picture slot with no picture or a placeholder;
            picture spaces still holding a placeholder; % of the teaching slides with interactive 3D (L67, counted as the
            course package counts it); the most words the room sees at once on one slide, and the slides over 120; claims
            not proved in the sources (fact_check.py); old-course findings (order, slides left out, thinner theory); Bloom
            lifts of more than one level; must-fix findings left in the script; how many slide templates and the longest
            run of one; the basic tasks of each self-check and the self-checks off their mix (t_sc_mix); simulator and
            equipment exercises written, and simulator drafts still awaiting the course director (L66). A number that
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
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from html.parser import HTMLParser

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content_script as cs  # noqa: E402
import course_portal  # noqa: E402
import workspace  # noqa: E402

TITLE = "FACTORY TRIAL"
MARKER = "FACTORY_TRIAL.json"
SIGNER = "Factory trial"
DECISIONS = ("intake.json", "kb_sources.json")
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

TRIAL_PROMPT = """You are the NOVIKONTAS course factory on a FACTORY TRIAL: a test build of a few modules after a factory update.
Nobody is there to answer. The course in this folder is "FACTORY TRIAL"; its source_files, old course and knowledge base are
here, and its decisions are already in course/working_claude (intake.json, kb_sources.json) - do not ask them again.
Use the course-factory skill and build it from scratch by its "Auto build" rules (SKILL.md), with these differences:
- Stage 1 and Stage 2 cover the whole programme as usual. Only modules {modules} get a content script, the fact-checker,
  a build and its checks; leave every other module unscripted.
- There is no expert: sign every STOP --by "Factory trial" (NOVIKONTAS_TRIAL=1 allows it). Never call course_portal.py -
  a trial never goes to the training app.
- Generate no paid pictures or videos; fill picture spaces from the free sources, and a space nobody could fill keeps its
  brief. Never push to git and never change a file outside this folder.
End with one line: TRIAL DONE, or TRIAL STOPPED: <why>."""


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


def setup(home, source, modules):
    """-> (config, problems)"""
    master = workspace.master_of(source) if hasattr(workspace, "master_of") else source
    master = os.path.abspath(master)
    course = os.path.join(master, "course") if os.path.isdir(os.path.join(master, "course")) else master
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


def prepare_run(home, cfg, modules, plugin_dir=None):
    """the new trial course: -> (master folder, run folder, prompt)"""
    master = os.path.join(home, "run", TITLE)
    remove_run(master)
    os.makedirs(os.path.join(master, "course", "working_claude"))
    save(os.path.join(master, MARKER), {"trial": True, "modules": modules, "from": cfg["from"],
                                        "plugin": plugin_version(plugin_dir), "started": datetime.now().strftime("%Y-%m-%d %H:%M")})
    for name in ("source_files", "old_course"):
        link(cfg["inputs"][name], os.path.join(master, name))
    for name in DECISIONS:
        src = os.path.join(home, "decisions", name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(master, "course", "working_claude", name))
    run_dir = os.path.join(home, "runs", datetime.now().strftime("%Y%m%d-%H%M") + "_" + plugin_version(plugin_dir))
    os.makedirs(run_dir, exist_ok=True)
    prompt = TRIAL_PROMPT.format(modules=", ".join(str(m) for m in modules))
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
    rev = load(workspace.claude_path(course, "pedagogy_review.json"), {}) or {}
    rows = ((rev.get("modules") or {}).get(str(m)) or {}).get("rows") or {}
    row["bloom_lifts_over_one"] = sum(1 for x in rows.values() if isinstance((x.get("now") or {}).get("level"), int)
                                      and isinstance((x.get("proposed") or {}).get("level"), int)
                                      and (x["now"]["level"] or 0) >= 1 and x["proposed"]["level"] - x["now"]["level"] > 1
                                      and not (x.get("proposed") or {}).get("expert"))
    if row["built"]:
        tpl = re.findall(r'data-template="([\w-]+)', io.open(deck, encoding="utf-8").read())
        run = best = 0
        for i, t in enumerate(tpl):
            run = run + 1 if i and t == tpl[i - 1] else 1
            best = max(best, run)
        row["templates"], row["same_template_in_a_row"] = len(set(tpl)), best
    sim = os.path.join(course, "additional-materials", "simulator-and-equipment")
    row["simulator_exercises"] = sum(1 for _, _, fs in os.walk(sim) for f in fs if re.match(r"%s_A\d+.*_TRAINEE\.pdf$" % mid, f))
    row["simulator_drafts_pending"] = measured(lambda: sum(1 for p in sim_pending(course) if p["module"] == m))
    return row


def sim_pending(course):
    """the drafted simulator tasks the course director has not accepted (L66, sim_coverage.py) - their minutes sit on a
    screen with no exercise behind it"""
    cov = os.path.join(os.path.dirname(HERE), "coverage", "scripts")
    if cov not in sys.path:
        sys.path.insert(0, cov)
    import sim_coverage
    return sim_coverage.pending(course)


LOWER_IS_BETTER = ("cut_or_cropped_slides", "cut_at_1024x768", "slides_3d_lagging", "claims_unproven", "claims_unchecked", "old_moved", "old_dropped",
                   "old_thinner", "must_fix_left", "bloom_lifts_over_one", "same_template_in_a_row", "build_minutes",
                   "off_blueprint_slides", "pictures_pending", "max_words_slide", "slides_over_120_words", "self_checks_off_mix",
                   "simulator_drafts_pending")
# a number that is best inside a band: closer to it is better (L67: 60-80 % of the teaching slides with interactive 3D)
BANDS = {"interactive_3d_share": (int(round(100 * cs.MEDIA["three_d"]["min_share"])), int(round(100 * cs.MEDIA["three_d"]["max_share"])))}
SHOWN = ("built", "passed", "build_says", "build_minutes", "cut_or_cropped_slides", "cut_at_1024x768", "slides_3d_lagging", "off_blueprint_slides",
         "pictures_pending", "interactive_3d_share", "max_words_slide", "slides_over_120_words", "claims", "claims_unproven",
         "claims_unchecked", "old_moved", "old_dropped", "old_thinner", "must_fix_left", "bloom_lifts_over_one", "templates",
         "same_template_in_a_row", "self_check_basic_tasks", "self_checks_off_mix", "simulator_exercises", "simulator_drafts_pending")


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
    a = ap.parse_args(argv)
    home = home_of(a.home)
    if a.cmd == "setup":
        mods = modules_of(a.modules or "1,4,8,19")
        if not a.source or not mods:
            print("Stopped - setup needs --from <the course's master folder> and --modules like 1,4,8,19")
            return 2
        cfg, probs = setup(home, a.source, mods)
        if probs:
            print("Stopped - " + "\n  ".join(probs))
            return 2
        print("Trial ready in %s - modules %s, from %s. Run it after every major update: factory_trial.py run"
              % (home, ", ".join(map(str, mods)), cfg["from"]))
        return 0
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
        master, run_dir, prompt = prepare_run(home, cfg, mods, a.plugin_dir)
    except OSError as err:
        print("Stopped - %s" % err)
        return 2
    cmd = claude_command(prompt, a.plugin_dir)
    if a.dry_run:
        print("Trial course made in %s (modules %s). Not started (--dry-run) - it would run:\n  %s\n  in %s"
              % (master, ", ".join(map(str, mods)), " ".join(cmd[:2]) + " <the trial prompt> " + " ".join(cmd[3:6]) + " ...", master))
        return 0
    env = course_portal.unattended_env(NOVIKONTAS_AUTO_BUILD="1", NOVIKONTAS_TRIAL="1")
    logf = os.path.join(run_dir, "build.log")
    print("Building the trial (modules %s) - this takes a while; the log, written as it goes: %s" % (", ".join(map(str, mods)), logf))
    rc = run_claude(cmd, master, env, logf)
    said = io.open(logf, encoding="utf-8", errors="replace").read()
    print("The build said: %s" % ([x for x in said.strip().splitlines() if x.strip()][-1:] or ["(nothing)"])[0][:200])
    code = report(home, run_dir)
    return code or (0 if rc == 0 and "TRIAL DONE" in said else 1)


if __name__ == "__main__":
    sys.exit(main())
