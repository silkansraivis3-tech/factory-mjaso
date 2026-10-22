# -*- coding: utf-8 -*-
"""test_build_course - the two passes of build_course.js, run in Node with stand-in agents (2.49.4).

    python test_build_course.py

Pass 1 (no `modules`) runs the reader and stops at the gate. Pass 2 (the approved table) never runs the
reader again - it would rewrite the architecture and the ILO map the owner has just approved - and a module
whose QA brought back nothing blocks instead of being counted clean.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WORKFLOW = os.path.join(HERE, "build_course.js")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FAILS = []

# The workflow body runs as an async function with stand-ins for the Workflow tool's agent / pipeline / phase.
HARNESS = r"""
const fs = require('fs')
const src = fs.readFileSync(process.argv[2], 'utf8').replace(/^export const meta/m, 'const meta')
const args = JSON.parse(process.argv[3])
const labels = [], opts = {}, prompts = {}
const agent = async (prompt, o) => {
  labels.push(o.label)
  opts[o.label] = { model: o.model || null, effort: o.effort || null }
  prompts[o.label] = prompt
  if (o.label.startsWith('gate:')) return { open: true, output: 'open', approved: args._approved || ['1', '2'] }
  if (o.label === 'qa:2') return null                       // the QA agent for module 2 brought back nothing
  if (o.label.startsWith('qa:')) return { module: o.label.slice(3), classification: 'OK', blocking: false, findings: [] }
  if (o.label.startsWith('read:')) return { modules: [] }
  const b = /^build:(\w+)$/.exec(o.label)                   // a builder: PASS, or (args._stuck) stopped mid-build
  if (b) return (args._stuck || []).indexOf(b[1]) >= 0 ? 'The first build is still running in the background.'
    : (args._pkgfail || []).indexOf(b[1]) >= 0 ? 'FAIL M0' + b[1] + ' - course package (60 s)' : 'PASS M0' + b[1] + ' - figures ... (40 s)'
  if (/^build:\w+\+\d+$/.test(o.label)) return 'PASS - carried on'
  return {}
}
const pipeline = (items, a, b) => Promise.all(items.map(async (x) => b(await a(x))))
const parallel = (fs_) => Promise.all(fs_.map((f) => f()))
const phase = () => {}
const log = () => {}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
new AsyncFunction('args', 'agent', 'pipeline', 'parallel', 'phase', 'log', src)(args, agent, pipeline, parallel, phase, log)
  .then((r) => console.log(JSON.stringify({ labels, opts, prompts, r })))
  .catch((e) => { console.log(JSON.stringify({ error: String(e && e.stack || e) })); process.exit(1) })
"""


def check(name, ok, detail=""):
    if not ok:
        FAILS.append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:600]) if detail and not ok else ""))


def run(tmp, args):
    h = os.path.join(tmp, "harness.cjs")
    with open(h, "w", encoding="utf-8") as f:
        f.write(HARNESS)
    p = subprocess.run(["node", h, WORKFLOW, json.dumps(args)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": p.stdout + p.stderr}


def main():
    if not shutil.which("node"):
        print("SKIP - no node")
        return 0
    tmp = tempfile.mkdtemp(prefix="build_course_")
    try:
        one = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf"})
        check("pass 1 (no modules): the reader runs, and the run stops at the gate",
              "error" not in one and one["labels"] == ["read:programme"] and one["r"].get("stopped_at") == "GATE", one)
        mods = [{"id": 1, "title": "A", "minutes": 60, "theory": 40, "practical": 20},
                {"id": 2, "title": "B", "minutes": 60, "theory": 40, "practical": 20}]
        two = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods})
        labels = two.get("labels", [])
        check("pass 2 (the approved table): the reader is NOT run again - the approved Stage 2 files stay as approved",
              "error" not in two and "read:programme" not in labels and labels[:1] == ["gate:ilo-map+kb"], two)
        check("... a module whose QA brought back nothing blocks; a module with a clean QA does not",
              two.get("r", {}).get("blocking") == ["2"], two.get("r"))
        o = two.get("opts", {})
        check("... an approved module is built and checked on Sonnet at medium effort (2.51.0)",
              o.get("build:1") == {"model": "sonnet", "effort": "medium"}
              and o.get("qa:1") == {"model": "sonnet", "effort": "medium"}, o)
        check("... the gate runs on Sonnet at low effort, and is asked every module's script status",
              o.get("gate:ilo-map+kb") == {"model": "sonnet", "effort": "low"}
              and two.get("prompts", {}).get("gate:ilo-map+kb", "").count("content_script.py status") == 2, o)
        check("... the builder runs build_module.py, not the compile and the checks one by one",
              "build_module.py" in two.get("prompts", {}).get("build:1", "")
              and "--no-course-pages" in two.get("prompts", {}).get("build:1", ""), two.get("prompts", {}).get("build:1"))
        b1 = two.get("prompts", {}).get("build:1", "")
        check("2.63.2: the builder answers L60's RECOMMENDED - the scene, or a declined_3d reason at the top of the sheet "
              "(M08, M10-M14 of the 2.63.0 build said nothing)",
              "RECOMMENDED (L60)" in b1 and "declined_3d" in b1 and "Never leave it unanswered" in b1, b1[-900:])
        qa1 = two.get("prompts", {}).get("qa:1", "")
        step2 = qa1.split("the checks it does not run", 1)[-1].split("The module's START_HERE", 1)[0]
        run_here, not_here = step2.split("NOT run here", 1) if "NOT run here" in step2 else (step2, "")
        check("2.63.2 the QA agent gets check_balance with the module's OWN minutes (--theory-min 40 --practice-min 20), "
              "never the whole course's programme total",
              "--theory-min 40 --practice-min 20" in run_here and "--programme" not in run_here.replace("never --programme alone", ""), qa1[-1500:])
        check("... and is told to run only the per-module checks: the whole-course tools are named as NOT run here",
              all(t in run_here for t in ("check_slide_text", "check_visual_first", "check_visuals", "check_assets", "classify_module"))
              and not any(t in run_here for t in ("check_hours", "check_syllabus_coverage", "crosscheck_tasks", "verify_links", "audit_navigation"))
              and all(t in not_here for t in ("check_hours", "check_syllabus_coverage", "crosscheck_tasks", "verify_links", "audit_navigation")),
              step2)
        three = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_approved": ["1"],
                          "factory": "C:/f/skills", "notes": "no paid pictures"})
        labels, o, pr = three.get("labels", []), three.get("opts", {}), three.get("prompts", {})
        check("a draft module gets its script written on the session's model, and no QA agent is spent on it",
              "script:2" in labels and "build:2" not in labels and "qa:2" not in labels
              and o.get("script:2") == {"model": None, "effort": None}
              and three.get("r", {}).get("blocking") == [], three)
        four = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_stuck": ["2"], "_pkgfail": ["1"],
                         "final": True, "factory": "C:/f/skills"})
        l4, o4, p4 = four.get("labels", []), four.get("opts", {}), four.get("prompts", {})
        check("2.58.0 a builder whose report has no PASS (it stopped mid-build) is carried on by a fresh agent, on Sonnet",
              "build:2+1" in l4 and o4.get("build:2+1") == {"model": "sonnet", "effort": "medium"}
              and "do NOT start again from --init-build" in p4.get("build:2+1", "") and "still running" in p4.get("build:2+1", ""), four)
        check("... one that passed, or failed only the course package (judged after assembly), is not",
              "build:1+1" not in l4 and not any(x.startswith("build:3") for x in l4), l4)
        check("... the builder is told to run build_module.py in the foreground and never end its turn while it runs",
              "IN THE FOREGROUND" in p4.get("build:1", ""), p4.get("build:1", "")[-900:])
        check("2.58.0 the final is built after the modules, then the course is assembled and its ILO map refreshed, "
              "and only then cross-checked",
              l4.index("build:final") > l4.index("qa:1") and l4.index("assemble:course") > l4.index("build:final")
              and l4.index("crosscheck:course") > l4.index("assemble:course")
              and "compile_course.py" in p4.get("assemble:course", "") and "ilo_map.py refresh" in p4.get("assemble:course", "")
              and "C:/f/skills/course-factory/scripts/check_course_package.py" in p4.get("assemble:course", ""), l4)
        check("2.63.2 the assembly runs the course-wide terminology report (a report, never a failure) and the cross-check reads it",
              "C:/f/skills/course-factory/retrofit/scripts/check_terms.py" in p4.get("assemble:course", "")
              and "REPORT, never a failure" in p4.get("assemble:course", "")
              and "check_terms.py" in p4.get("crosscheck:course", "") and "check_language.py" in p4.get("crosscheck:course", ""), p4.get("assemble:course"))
        l5 = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "wave": 1}).get("labels", [])
        check("args.wave builds the modules in waves: module 2 starts after module 1's QA",
              l5.index("build:2") > l5.index("qa:1") and "build:final" not in l5, l5)
        check("args.factory pins the skills every agent reads, args.notes reaches every module agent",
              "C:/f/skills/course-factory/SKILL.md" in pr.get("build:1", "")
              and "C:/f/skills/course-factory/scripts/course_gate.py" in pr.get("gate:ilo-map+kb", "")
              and "no paid pictures" in pr.get("build:1", "") and "no paid pictures" in pr.get("script:2", ""), pr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
