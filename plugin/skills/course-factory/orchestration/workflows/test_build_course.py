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
  return {}
}
const pipeline = (items, a, b) => Promise.all(items.map(async (x) => b(await a(x))))
const parallel = (fs_) => Promise.all(fs_.map((f) => f()))
const phase = () => {}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
new AsyncFunction('args', 'agent', 'pipeline', 'parallel', 'phase', src)(args, agent, pipeline, parallel, phase)
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
        three = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_approved": ["1"],
                          "factory": "C:/f/skills", "notes": "no paid pictures"})
        labels, o, pr = three.get("labels", []), three.get("opts", {}), three.get("prompts", {})
        check("a draft module gets its script written on the session's model, and no QA agent is spent on it",
              "script:2" in labels and "build:2" not in labels and "qa:2" not in labels
              and o.get("script:2") == {"model": None, "effort": None}
              and three.get("r", {}).get("blocking") == [], three)
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
