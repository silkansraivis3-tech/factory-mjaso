# -*- coding: utf-8 -*-
"""phase_a.py - every approved module built as far as it goes with NO agent, in one local queue (2.73.0).

    phase_a.py <course> --modules 1,2,5-9 [--jobs N] [--no-auto]     start (or join) the run; answers within 9 min
    phase_a.py <course> --wait                                          wait for the run that said STILL RUNNING

WHY (chem advanced, 2026-10-27): 18 builder agents at once hit the 20-subagent cap, pinned the CPU at 100 % and queued on
3 browser slots and the cold-build lock - the agents mostly waited, and each wait was a model turn. Phase A needs no model:
for each module, in a queue sized by this computer (browser_slots.py: each build takes up to three hidden browsers):

  1  compile_module.py --init-build when it has no build sheet (a sheet from before 2.73.0: --fill-slots) - every picture
     slot filled with its placeholder, starter figure or 3D starter;
  2  build_module.py --no-course-pages --auto - every check that does not depend on the pictures; then (--auto) each slide's
     photo slot whose course-catalogue pick is good enough takes it, and the module is built once more.

Each module ends PASS (nothing left for an agent - it still goes to the visual review), MODULE CLEAN, PHASE A CLEAN (its
needs file, working_claude\\visuals\\MNN_VISUAL_NEEDS.md, is the Phase B agent's whole brief) or FAIL (its build's own
answer says what). The run's answer, one line per module: working_claude\\_build\\PHASE_A.json and its last lines here.
Run working_claude\\photo_catalogue.json / photo_plan.json first (scripts\\photo_catalogue.py index / assign) so --auto has
picks. Like build_module.py, a run longer than 9 minutes goes on by itself and answers STILL RUNNING (exit 3): --wait.
Exit 0 every module reached PASS, MODULE CLEAN or PHASE A CLEAN; 1 a module failed; 3 still running.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(SKILLS, "course-factory", "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY = sys.executable
ANSWER_WITHIN = 540
LAST = re.compile(r"^(PASS|PHASE A CLEAN|FAIL|MODULE CLEAN|STILL BUILDING)\b.*$", re.M)


def modules_of(text):
    out = []
    for part in str(text or "").split(","):
        part = part.strip()
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            out += list(range(int(m.group(1)), int(m.group(2)) + 1))
        elif part.isdigit():
            out.append(int(part))
    return out


def run(cmd, timeout=3600):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def one(course, n, auto):
    """a module through Phase A: (n, exit code, its answer's key line, seconds)"""
    import compile_module as cm
    import build_module as bm
    t0 = time.time()
    if not os.path.isfile(cm.build_path(course, n)):
        code, out = run([PY, os.path.join(HERE, "compile_module.py"), course, "--module", str(n), "--init-build"])
        if code != 0:
            return n, 2, "FAIL M%02d - --init-build stopped: %s" % (n, out.strip().splitlines()[-1] if out.strip() else "?"), time.time() - t0
    elif bm.starter_blanks(course, n):
        run([PY, os.path.join(HERE, "compile_module.py"), course, "--module", str(n), "--fill-slots"])
    cmd = [PY, os.path.join(HERE, "build_module.py"), course, "--module", str(n), "--no-course-pages", "--inner"]
    code, out = run(cmd + (["--auto"] if auto else []))
    lines = LAST.findall(out)
    keys = [x for x in out.splitlines() if LAST.match(x)]
    key = keys[-1] if keys else (out.strip().splitlines() or ["(no answer)"])[-1]
    if "MODULE CLEAN" in out:
        key = "MODULE CLEAN M%02d - only the course package is left (judged after assembly)" % n
    return n, code, key, time.time() - t0


def jobs_default():
    try:
        import browser_slots
        return max(1, browser_slots.count() // 3)
    except Exception:                                    # noqa: BLE001
        return 1


def status_paths(course):
    import workspace
    d = workspace.claude_path(workspace.work_folder(course, create=False), "_build")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "PHASE_A.json"), os.path.join(d, "PHASE_A_running.json")


def inner(course, mods, jobs, auto):
    import workspace
    course = workspace.work_folder(course, create=False)
    res_p, run_p = status_paths(course)
    rows = {}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        for n, code, key, secs in ex.map(lambda k: one(course, k, auto), mods):
            rows["M%02d" % n] = {"exit": code, "answer": key, "seconds": round(secs)}
            io.open(res_p, "w", encoding="utf-8").write(json.dumps(rows, indent=1, ensure_ascii=False))
    rec = json.load(io.open(run_p, encoding="utf-8")) if os.path.isfile(run_p) else {}
    rec["exit"] = 0 if all(r["exit"] in (0, 4) or "MODULE CLEAN" in r["answer"] for r in rows.values()) else 1
    io.open(run_p, "w", encoding="utf-8").write(json.dumps(rec))
    return rec["exit"]


def answer(course):
    res_p, run_p = status_paths(course)
    rows = json.load(io.open(res_p, encoding="utf-8")) if os.path.isfile(res_p) else {}
    for k in sorted(rows):
        print("%s  %4ds  %s" % (k, rows[k]["seconds"], rows[k]["answer"]))
    phase_b = [k for k in sorted(rows) if rows[k]["exit"] == 4]
    if phase_b:
        print("Phase B - pictures to fill: %s (each module's working_claude\\visuals\\MNN_VISUAL_NEEDS.md is its whole brief)"
              % ", ".join(phase_b))
    rec = json.load(io.open(run_p, encoding="utf-8")) if os.path.isfile(run_p) else {}
    return rec.get("exit", 1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--modules")
    ap.add_argument("--jobs", type=int, default=0)
    ap.add_argument("--no-auto", action="store_true")
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--inner", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    mods = modules_of(a.modules)
    jobs = a.jobs or jobs_default()
    if a.inner:
        return inner(a.course, mods, jobs, not a.no_auto)
    import browser_slots
    res_p, run_p = status_paths(a.course)
    rec = json.load(io.open(run_p, encoding="utf-8")) if os.path.isfile(run_p) else {}
    running = rec.get("exit") is None and rec.get("pid") and browser_slots.alive(int(rec["pid"]))
    if not running and not a.wait:
        if not mods:
            print("Stopped - name the modules: --modules 1,2,5-9")
            return 2
        if os.path.isfile(res_p):
            os.remove(res_p)
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000) if os.name == "nt" else 0
        log = io.open(res_p.replace(".json", ".log"), "w", encoding="utf-8")
        p = subprocess.Popen([PY, os.path.abspath(__file__), a.course, "--modules", a.modules, "--jobs", str(jobs), "--inner"]
                             + (["--no-auto"] if a.no_auto else []), stdout=log, stderr=subprocess.STDOUT,
                             env=dict(os.environ, PYTHONIOENCODING="utf-8"), creationflags=flags,
                             **({} if os.name == "nt" else {"start_new_session": True}))
        log.close()
        io.open(run_p, "w", encoding="utf-8").write(json.dumps({"pid": p.pid, "started": time.time(), "modules": mods, "jobs": jobs}))
        print("Phase A started: modules %s, %d at a time (no agent)" % (", ".join(str(x) for x in mods), jobs))
    elif not rec:
        print("No Phase A run to wait for")
        return 1
    t0 = time.time()
    while time.time() - t0 < ANSWER_WITHIN:
        rec = json.load(io.open(run_p, encoding="utf-8")) if os.path.isfile(run_p) else {}
        if rec.get("exit") is not None or not browser_slots.alive(int(rec.get("pid") or 0)):
            return answer(a.course)
        time.sleep(2)
    answer(a.course)
    print("STILL RUNNING - the run goes on by itself; run phase_a.py <course> --wait for its answer")
    return 3


if __name__ == "__main__":
    sys.exit(main())
