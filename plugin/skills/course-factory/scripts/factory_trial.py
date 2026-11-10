#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The factory trial - a few modules of a real course built from scratch after every major update, and scored.

    factory_trial.py setup  --from <course master folder> [--modules 1,4,8,19] [--home <folder>]
    factory_trial.py run    [--modules 1,4] [--plugin-dir <plugin folder>] [--dry-run] [--home <folder>]
    factory_trial.py report [--run <runs\\folder>] [--no-browser] [--home <folder>]
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
          the installed one (a release before it is pushed). The log and the score go to runs\\<date>\\. Then report.
  report  the scorecard of each trial module, and what changed since the last trial:
            built and its build's last line; slides cut or pictures cropped at 1280 x 800 (fit_gate.py); 3D slides
            that lag on a slowed CPU (perf_gate.py); claims not
            proved in the sources (fact_check.py); old-course findings (order, slides left out, thinner theory); Bloom
            lifts of more than one level; must-fix findings left in the script; how many slide templates and the longest
            run of one; simulator and equipment exercises written.
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
    cmd = course_portal.claude_command(prompt)
    return cmd + (["--plugin-dir", os.path.abspath(plugin_dir)] if plugin_dir else [])


# ------------------------------------------------------------------ the scorecard
def module_dir(course, m):
    return os.path.join(course, workspace.MODULES, "module%02d" % m)


def fit_slides(deck, no_browser):
    if no_browser or not os.path.isfile(deck):
        return None
    sys.path.insert(0, os.path.join(PLUGIN, "skills", "course-module-ux", "measure", "scripts"))
    import contextlib
    import fit_gate
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = fit_gate.main([deck, "--viewport", "1280x800"])
    m = re.search(r"FAIL (\d+) slide", buf.getvalue())
    return int(m.group(1)) if m else (0 if code == 0 else None)


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
    ans = os.path.join(course, "working_claude", "_build", "%s_answer.txt" % mid)
    last = [x.strip() for x in io.open(ans, encoding="utf-8", errors="replace").read().splitlines() if x.strip()][-1:] \
        if os.path.isfile(ans) else []
    row["build_says"] = last[0][:90] if last else ""
    row["cut_or_cropped_slides"] = fit_slides(deck, no_browser)
    row["slides_3d_lagging"] = perf_slides(deck, no_browser)
    if script:
        import fact_check
        if fact_check.course_kbs(course):
            st = fact_check.status(course, m, script)
            row["claims"], row["claims_unproven"], row["claims_unchecked"] = st["claims"], len(st["unproven"]), len(st["unchecked"])
        old = cs.old_course_findings(course, script)
        for rule in ("o_moved", "o_dropped", "o_thinner"):
            row[rule.replace("o_", "old_")] = sum(1 for f in old if f["rule"] == rule)
        row["must_fix_left"] = len(cs.blocking(cs.all_findings(script, course)))
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
    return row


LOWER_IS_BETTER = ("cut_or_cropped_slides", "slides_3d_lagging", "claims_unproven", "claims_unchecked", "old_moved", "old_dropped", "old_thinner",
                   "must_fix_left", "bloom_lifts_over_one", "same_template_in_a_row")


def compare(now, before):
    """[(module, metric, before, now, better or worse)] for every number that moved"""
    out = []
    old = {r["module"]: r for r in (before or {}).get("modules", [])}
    for r in now.get("modules", []):
        b = old.get(r["module"]) or {}
        for k, v in r.items():
            if k == "module" or not isinstance(v, (int, float)) or isinstance(v, bool) or not isinstance(b.get(k), (int, float)) \
                    or b.get(k) == v:
                continue
            down = v < b[k]
            out.append((r["module"], k, b[k], v, "better" if down == (k in LOWER_IS_BETTER) else "worse"))
    return out


def report(home, run_dir=None, no_browser=False):
    cfg = load(os.path.join(home, "trial.json"))
    master = os.path.join(home, "run", TITLE)
    mark = load(os.path.join(master, MARKER))
    if not cfg or not mark:
        print("No trial course to score - setup, then run.")
        return 2
    course = os.path.join(master, "course")
    runs = sorted(d for d in os.listdir(os.path.join(home, "runs")) if os.path.isdir(os.path.join(home, "runs", d)))
    run_dir = run_dir or (os.path.join(home, "runs", runs[-1]) if runs else os.path.join(home, "runs", "report"))
    card = {"plugin": mark.get("plugin"), "started": mark.get("started"), "scored": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "modules": [score_module(course, m, no_browser) for m in mark.get("modules") or []]}
    save(os.path.join(run_dir, "scorecard.json"), card)
    before = None
    for d in reversed(runs):
        p = os.path.join(home, "runs", d, "scorecard.json")
        if os.path.abspath(os.path.join(home, "runs", d)) != os.path.abspath(run_dir) and os.path.isfile(p):
            before = load(p)
            break
    print("FACTORY TRIAL - course-factory %s, started %s" % (card["plugin"], card["started"]))
    keys = [k for k in ("built", "build_says", "cut_or_cropped_slides", "slides_3d_lagging", "claims", "claims_unproven", "claims_unchecked", "old_moved",
                        "old_dropped", "old_thinner", "must_fix_left", "bloom_lifts_over_one", "templates", "same_template_in_a_row",
                        "simulator_exercises")]
    for r in card["modules"]:
        print("\nModule %d" % r["module"])
        for k in keys:
            if k in r:
                print("  %-24s %s" % (k.replace("_", " "), "-" if r[k] is None else r[k]))
    moved = compare(card, before)
    if before:
        print("\nSince the last trial (course-factory %s):" % before.get("plugin"))
        for m, k, b, v, how in moved or []:
            print("  M%02d %-24s %s -> %s  %s" % (m, k.replace("_", " "), b, v, how.upper() if how == "worse" else how))
        if not moved:
            print("  nothing moved")
    print("\n    %s" % os.path.join(run_dir, "scorecard.json"))
    return 1 if any(x[4] == "worse" for x in moved) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("setup", "run", "report", "status"))
    ap.add_argument("--home")
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
        return report(home, a.run, a.no_browser)
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
    env = dict(os.environ, NOVIKONTAS_AUTO_BUILD="1", NOVIKONTAS_TRIAL="1")
    logf = os.path.join(run_dir, "build.log")
    print("Building the trial (modules %s) - this takes a while; the log: %s" % (", ".join(map(str, mods)), logf))
    with io.open(logf, "w", encoding="utf-8") as out:
        r = subprocess.run(cmd, cwd=master, stdout=out, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                           env=env, timeout=20 * 3600)
    said = io.open(logf, encoding="utf-8", errors="replace").read()
    print("The build said: %s" % ([x for x in said.strip().splitlines() if x.strip()][-1:] or ["(nothing)"])[0][:200])
    code = report(home, run_dir)
    return code or (0 if r.returncode == 0 and "TRIAL DONE" in said else 1)


if __name__ == "__main__":
    sys.exit(main())
