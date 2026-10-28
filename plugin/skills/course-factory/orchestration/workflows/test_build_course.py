# -*- coding: utf-8 -*-
"""test_build_course - the two passes of build_course.js, run in Node with stand-in agents (2.49.4).

    python test_build_course.py

Pass 1 (no `modules`) runs the reader and stops at the gate. Pass 2 (the approved table) never runs the
reader again - it would rewrite the architecture and the ILO map the owner has just approved - and a module
whose QA brought back nothing blocks instead of being counted clean.
"""
from __future__ import annotations

import io
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
let figActive = 0, figMax = 0                              // 2.72.7: figure fixers at once
let building = 0, most = 0                                // builds at once (2.65.0: the pool), when args._slow
const agent = async (prompt, o) => {
  labels.push(o.label)
  if (args._slow && /^(build|fix):/.test(o.label)) {
    most = Math.max(most, ++building)
    await new Promise((go) => setTimeout(go, 30 * ((args._slow[o.label] || 1))))
    building--
  }
  opts[o.label] = { model: o.model || null, effort: o.effort || null }
  prompts[o.label] = prompt
  if (o.label.startsWith('fixfig:')) {
    figActive++; figMax = Math.max(figMax, figActive)
    await new Promise((r) => setTimeout(r, 5))
    figActive--
    return 'fixed the figure'
  }
  if (o.label.startsWith('gate:')) return { open: true, output: 'open', approved: args._approved || ['1', '2'], order: args._order || [],
                                            skill_dir: args._skill_dir }
  if (/^3d:/.test(o.label)) return (args._scene || []).indexOf(o.label.slice(3).split('+')[0]) >= 0
    ? { has_scene: true, ok: true, shots: ['C:/c/r/s05_step1.png'], scenes: [{ slide: 's05', spec: 's05.kit3d.json' }] }
    : { has_scene: false, ok: true, shots: [] }
  if (/^fix3d:/.test(o.label)) return { has_scene: true, ok: true, shots: ['C:/c/r/s05_step1.png'] }
  if (/^review3d:/.test(o.label)) return (args._bad3d || []).indexOf(o.label.slice(9)) >= 0
    ? { findings: [{ severity: 'BROKEN', where: 's05 s05_step1.png', what: 'the labels are a row of buttons under the model' }] }
    : { findings: [] }
  if (/^figshots:/.test(o.label)) return (args._figs || []).indexOf(o.label.slice(9).split('+')[0]) >= 0
    ? { has_figures: true, manifest: 'C:/c/working_claude/review/M0' + o.label.slice(9, 10) + '_figures/figures.json' }
    : { has_figures: false, manifest: '' }
  if (/^reviewfig:/.test(o.label) && (args._manyfigs || []).indexOf(o.label.slice(10)) >= 0)    // five broken figures
    return { figures: ['s03', 's04', 's05', 's06', 's07'].map((s) => ({ slide: s, shows: 'a pipe', seafarer_ok: false,
                                                                         findings: [{ severity: 'BROKEN', what: s + ': a pipe ends on nothing' }] })) }
  if (/^reviewfig:/.test(o.label)) return ((args._badfig || []).indexOf(o.label.slice(10)) >= 0
                                          || (args._stillbad || []).indexOf(o.label.slice(10).replace('+fix', '')) >= 0)
    ? { figures: [{ slide: 's03', shows: 'a ship with the vent mast inside the hull', seafarer_ok: false,
                    findings: [{ severity: 'BROKEN', what: 'the vent mast stands inside the hull, under the deck' },
                               { severity: 'POLISH', what: 'a label could sit closer' }] }] }
    : { figures: [{ slide: 's03', shows: 'a ship side view', seafarer_ok: true, findings: [] }] }
  if (o.label === 'qa:2') return null                       // the QA agent for module 2 brought back nothing
  if ((args._broken || []).indexOf(o.label.slice(3)) >= 0)  // a QA that found a picture of another thing (2.63.3)
    return { module: o.label.slice(3), classification: 'A', blocking: true,
             findings: [{ severity: 'BROKEN', where: 's03', what: 'an oxygen monitor on a %LEL slide' },
                        { severity: 'BROKEN', where: 'SCRIPT: s05', what: 'a Your turn activity counts 5 practice minutes' },
                        { severity: 'POLISH', where: 's05', what: 'a label could sit closer' }] }
  if ((args._scriptonly || []).indexOf(o.label.slice(3)) >= 0)  // only the operator can fix it (the approved script)
    return { module: o.label.slice(3), classification: 'A', blocking: true,
             findings: [{ severity: 'BROKEN', where: 'SCRIPT: s05', what: 'a Your turn activity counts 5 practice minutes' }] }
  if (o.label.startsWith('qa:')) return { module: o.label.slice(3), classification: 'OK', blocking: false, findings: [] }
  if (o.label.startsWith('fix:')) return 'PASS - fixed'
  if (o.label.startsWith('read:')) return { modules: [] }
  if (o.label === 'phase-a:modules') return args._phase_a ? { modules: args._phase_a } : {}   // 2.73.0 Phase A's lines
  const b = /^build:(\w+)$/.exec(o.label)                   // a builder: PASS, or (args._stuck) stopped mid-build
  if (b) return (args._stuck || []).indexOf(b[1]) >= 0 ? 'The first build is still running in the background.'
    : (args._listed || []).indexOf(b[1]) >= 0     // 2.72.7: stopped on a FAIL by the stop rule, what is left listed
      ? 'FAIL M0' + b[1] + ' - audits 1280x800 1024x768 (97 s)\nSTOP - everything this build prints has failed 3 builds running\n'
        + 'Left as it is: s05 scrolls div.slide-body'
    : (args._pkgfail || []).indexOf(b[1]) >= 0 ? 'FAIL M0' + b[1] + ' - course package (60 s)' : 'PASS M0' + b[1] + ' - figures ... (40 s)'
      + ((args._time || {})[b[1]] ? '\nTIME M0' + b[1] + ': ' + args._time[b[1]] + ' min from its starter build sheet to its first PASS - x' : '')
  if (/^build:\w+\+\d+$/.test(o.label)) return 'PASS - carried on'
  return {}
}
const pipeline = (items, ...stages) => Promise.all(items.map(async (x) => { let r = x; for (const s of stages) r = await s(r); return r }))
const parallel = (fs_) => Promise.all(fs_.map((f) => f()))
const phase = () => {}
const log = () => {}
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
new AsyncFunction('args', 'agent', 'pipeline', 'parallel', 'phase', 'log', src)(args, agent, pipeline, parallel, phase, log)
  .then((r) => console.log(JSON.stringify({ labels, opts, prompts, r, figMax, most })))
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
        b1 = two.get("prompts", {}).get("build:1", "")
        check("2.65.0: the builder's report carries build_module.py's TIME line (the gold standard: 30-40 min a module)",
              'its SECOND line the "TIME M0N: ..."' in b1 and "30-40 minutes a module" in b1, b1[-700:])
        timed = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_approved": ["1", "2"],
                          "_time": {"1": 52}})
        g = timed.get("r", {}).get("gold_standard", {})
        check("... and the workflow's answer lists each module's minutes, and which went over the 40",
              g.get("minutes") == [{"module": "1", "minutes": 52}] and g.get("over") == ["1"]
              and "20 min for its fixes" in g.get("target", ""), timed.get("r", {}).get("gold_standard") or timed)
        sized = [{"id": 1, "title": "A", "minutes": 40, "theory": 30, "practical": 10},
                 {"id": 2, "title": "B", "minutes": 200, "theory": 150, "practical": 50},
                 {"id": 3, "title": "C", "minutes": 80, "theory": 60, "practical": 20},
                 {"id": 4, "title": "D", "minutes": 300, "theory": 200, "practical": 100}]
        big = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": sized, "wave": 2, "_approved": ["1", "2", "3"]})
        builds = [x for x in big.get("labels", []) if x.startswith("build:")]
        check("2.65.0: the biggest approved module is built first (200, 80, 40 min); a draft's script writer takes no "
              "build place", builds == ["build:2", "build:3", "build:1"] and "script:4" in big.get("labels", []),
              big.get("labels") or big)
        sized4 = [dict(x, id=x["id"]) for x in sized]
        pool = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": sized4, "wave": 2,
                         "_approved": ["1", "2", "3", "4"], "_slow": {"build:4": 6}})
        lp = pool.get("labels", [])
        check("... a rolling pool, never more than A.wave builds at once: while the biggest (300 min) still builds, the "
              "next ones start as each build ends - no wave waits for its slowest module",
              pool.get("most") == 2 and lp.index("build:1") < lp.index("qa:4"), lp)
        check("... and every module is still judged: the one whose QA brought back nothing blocks, under its own number",
              big.get("r", {}).get("blocking") == ["2"], big.get("r"))
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
        check("2.72.7 QA leaves the kit figures to the figure review: words, ILO teaching, task pages, photos and the build "
              "are its own; a kit figure's drawing is never its finding (2.72.5: ~13-16 of QA's 24 first BROKEN were figures)",
              "NOT YOURS - the kit figures" in qa1 and "FIGURE review judges every one" in qa1
              and "the words, the ILO teaching, the task pages, the photographs and the build" in qa1
              and "Does each figure teach something" not in qa1 and "drawing that is not a kit figure" in qa1
              and "only the slide around it" in qa1, qa1[:3000])
        tail = qa1.split("Next alone?", 1)[-1].split("A module that still classifies C", 1)[0]
        with open(os.path.join(HERE, "..", "..", "compile", "REVIEW_PROMPT.md"), encoding="utf-8") as f:
            review = f.read()
        check("2.63.2 the QA agent asks whether each picture shows what the question / slide names (an oxygen monitor on a %LEL "
              "question) and a different instrument or part is BROKEN",
              "show what the question or slide NAMES" in tail and "%LEL question" in tail and "spectacle blind" in tail
              and "severity BROKEN" in tail and "REVIEW_PROMPT.md, item 6" in tail, tail)
        rv_item6 = review.split("6. **The picture shows what the words name**", 1)[-1].split("**A re-review**", 1)[0]
        rv_broken = review.split("- `BROKEN` -", 1)[-1].split("- `POLISH`", 1)[0]
        check("2.63.2 REVIEW_PROMPT.md has the rule as item 6 - the picture is the instrument / part / place the words name - "
              "and lists a different one under BROKEN (the sheets' reviewer, item numbers 1-7 since 2.72.0)",
              "6. **The picture shows what the words name**" in review and "oxygen monitor on a %LEL" in rv_item6
              and "portable explosimeter" in rv_item6 and "spectacle blind" in rv_item6
              and "different instrument, part" in rv_broken and "item number (1-7)" in review, review[-1200:])
        check("2.72.0 REVIEW_PROMPT.md item 7: a drawing a seafarer calls wrong (inside the hull, a named part missing, "
              "unconnected, floating, incomplete) is BROKEN, never POLISH; so is it in the QA prompt",
              "7. **The drawing is physically right and complete**" in review and "item 7" in rv_broken
              and "(item 7) is BROKEN,\nnever POLISH" in review and "a minuscule detail is not that" in review
              and "never POLISH (REVIEW_PROMPT.md item 7)" in open(WORKFLOW, encoding="utf-8").read())
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
        # 2.72.7 - the 2.72.5 run: both retries (21 / 27 min, 28 builds) ended without PASS on findings the fixer got anyway
        lst = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_listed": ["2"], "factory": "C:/f/skills"})
        ll = lst.get("labels", [])
        check("2.72.7 a builder that stopped on a build's FAIL and listed what is left gets NO retry - its module goes to the "
              "judges (2.72.5: both retries ended without PASS)",
              "error" not in lst and "build:2+1" not in ll and "qa:2" in ll and ll.index("qa:2") > ll.index("build:2"), lst)
        b2 = lst.get("prompts", {}).get("build:2", "")
        with open(os.path.join(HERE, "..", "..", "compile", "BUILDER_CARD.md"), encoding="utf-8") as f:
            card0 = f.read()
        check("... the builder and its card have the stop rule: the same finding three builds running is listed, never built "
              "for again; STOP when everything left is such a finding",
              "THE SAME FINDING THREE BUILDS RUNNING" in b2 and "SAME FINDING 3 BUILDS RUNNING" in b2
              and "SAME FINDING 3 BUILDS RUNNING" in card0 and "three builds running" in card0.split("## Stop", 1)[-1], b2[-1600:])
        check("2.58.0 the final is built after the modules, then the course is assembled and its ILO map refreshed, "
              "and only then cross-checked",
              l4.index("build:final") > l4.index("qa:1") and l4.index("assemble:course") > l4.index("build:final")
              and l4.index("crosscheck:course") > l4.index("assemble:course")
              and "compile_course.py" in p4.get("assemble:course", "") and "ilo_map.py refresh" in p4.get("assemble:course", "")
              and "C:/f/skills/course-factory/scripts/check_course_package.py" in p4.get("assemble:course", ""), l4)
        check("2.63.2 the assembly runs the course-wide terminology report (a report, never a failure) and the cross-check reads it",
              "C:/f/skills/course-factory/retrofit/scripts/check_terms.py" in p4.get("assemble:course", "")
              and "REPORTS, never a failure" in p4.get("assemble:course", "")
              and "check_terms.py" in p4.get("crosscheck:course", "") and "check_language.py" in p4.get("crosscheck:course", ""), p4.get("assemble:course"))
        check("2.63.2 the assembly also runs the course-wide number report (a report, never a failure) and the cross-check reads it",
              "C:/f/skills/course-factory/retrofit/scripts/check_numbers.py" in p4.get("assemble:course", "")
              and "Both are REPORTS, never a failure" in p4.get("assemble:course", "")
              and "check_numbers.py" in p4.get("crosscheck:course", "") and "one quantity, one value" in p4.get("crosscheck:course", ""),
              p4.get("assemble:course"))
        # 2.63.3 (the 2.63.2 full-course run: 46 of 128 build calls after module clean, builders reviewing their own sheets)
        check("2.63.3 the builder stops at module clean and does not review its own sheets",
              "STOP AT MODULE CLEAN" in b1 and "Do NOT review the sheets" in b1 and "review the sheets yourself against it" not in b1, b1[-2500:])
        check("... and waits for a long build with --wait instead of blind (STILL BUILDING)",
              "STILL BUILDING" in b1 and "--wait" in b1 and "600000" in b1, b1[-1500:])
        check("2.63.3 the QA agent does the one visual review on the promoted sheets, marks them reviewed, keeps POLISH outside "
              "the folder, and grades BROKEN / POLISH / INFO",
              "THE ONE VISUAL REVIEW" in qa1 and "--reviewed" in qa1 and "M01_POLISH.md" in qa1 and "Look at\neach sheet ONCE" in qa1
              and "BROKEN" in qa1 and "POLISH" in qa1 and "INFO" in qa1, qa1[-2000:])
        with open(WORKFLOW, encoding="utf-8") as f:
            wsrc = f.read()
        check("... the QA schema's severity is the enum BROKEN / POLISH / INFO (five scales in the 2.63.2 run)",
              "enum: ['BROKEN', 'POLISH', 'INFO']" in wsrc)
        check("... a clean QA sends nothing back", not any(x.startswith("fix:") for x in labels), labels)
        fig = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_figs": ["1", "2"], "_badfig": ["1"],
                        "factory": "C:/f/skills"})
        lf, pf = fig.get("labels", []), fig.get("prompts", {})
        check("2.72.0 the FIGURE step: every module with kit figures is photographed at projector size (figure_review.py) "
              "and judged by a separate reviewer - 2.72.5: at the same time as QA (QA starts before the figure review ends)",
              "figshots:1" in lf and "reviewfig:1" in lf and "reviewfig:2" in lf and lf.index("qa:1") < lf.index("reviewfig:1")
              and "figure_review.py" in pf.get("figshots:1", "") and "1920 x 1080" in pf.get("reviewfig:1", "")
              and "seafarer" in pf.get("reviewfig:1", ""), lf)
        ff = pf.get("fixfig:1:s03", "")
        check("... its BROKEN findings (not POLISH) go back ONCE - 2.72.7: to a fixer of that one figure (start from a pattern, "
              "place by relations), then ONE build - then only those figures are photographed and judged again; a clean module "
              "sends nothing back",
              lf.count("fixfig:1:s03") == 1 and "inside the hull" in ff and "could sit closer" not in ff
              and "Relations" in ff and "patterns" in ff and "fix:1" not in lf and lf.count("fixbuild:1") == 1
              and lf.index("fixfig:1:s03") > max(lf.index("reviewfig:1"), lf.index("qa:1"))
              and lf.index("fixbuild:1") > lf.index("fixfig:1:s03") and lf.index("figshots:1+fix") > lf.index("fixbuild:1")
              and "--only s03" in pf.get("figshots:1+fix", "") and "reviewfig:1+fix" in lf and not any(x.startswith(("fix:2", "fixfig:2")) for x in lf)
              and "qa:1+fix" not in lf, lf)
        check("2.72.7 a figure fixer writes only its own spec, never builds, iterates in the studio (--quick, the meaning checks, "
              "one --step all) with AT MOST SIX studio runs; the one build after it has AT MOST TWO runs",
              "YOU MAY WRITE ONLY THAT ONE SPEC FILE" in ff and "NEVER run\nbuild_module.py" in ff and "studio.py" in ff
              and "--quick" in ff and "kit_meaning.py" in ff and "--step all" in ff and "AT MOST SIX studio runs" in ff
              and "AT MOST TWO build_module.py\nruns" in pf.get("fixbuild:1", "") and "STOP whatever it prints" in pf.get("fixbuild:1", ""),
              (ff[-1500:], pf.get("fixbuild:1", "")[-800:]))
        b1f = pf.get("build:1", "")
        with open(os.path.join(HERE, "..", "..", "compile", "BUILDER_CARD.md"), encoding="utf-8") as f:
            card = f.read()
        check("2.72.0 the builder BUILDS FIRST: the starters are drawn, never deleted or rewritten, no figure polished that the "
              "build did not name (the first proof run's builders redrew every figure by hand: 50 min, nothing built)",
              "then BUILD" in b1f and "never delete" in b1f and "the build PRINTED" in b1f
              and "BUILD FIRST" in card and "never delete or rewrite a starter" in card, b1f[:1500])
        still = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_figs": ["1"], "_stillbad": ["1"],
                          "factory": "C:/f/skills"})
        ls = still.get("labels", [])
        q1 = [q for q in (still.get("r") or {}).get("qa", []) if q and q.get("module") == "1"]
        check("2.72.0 NOTHING LOOPS: a figure still BROKEN after the one fix round goes on the operator's list (for_aleksis), "
              "never a second fixfig, and the module is not failed for it; the reviewer gets BLOCK / NOTE / waived and the "
              "fix round may accept a finding with a reason (meaning_ok)",
              ls.count("fixfig:1:s03") == 1 and ls.count("fixbuild:1") == 1 and q1 and any("FIGURE s03" in x for x in q1[0].get("for_aleksis", []))
              and not q1[0].get("blocking") and '"block"' in pf.get("reviewfig:1", "") and '"note"' in pf.get("reviewfig:1", "")
              and '"waived"' in pf.get("reviewfig:1", "") and "meaning_ok" in pf.get("fixfig:1:s03", ""), q1)
        six = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_broken": ["1"]})
        l6, p6 = six.get("labels", []), six.get("prompts", {})
        check("2.63.3 a BROKEN QA finding sends the module back for ONE fix round, then QA once more - never a third",
              "fix:1" in l6 and l6.index("fix:1") > l6.index("qa:1") and l6.index("qa:1+fix") > l6.index("fix:1")
              and l6.count("fix:1") == 1 and not any(x.startswith("fix:2") for x in l6), l6)
        check("... the fix round is told exactly the BROKEN findings (not the POLISH), not to start again, and to stop at module clean",
              "s03: an oxygen monitor on a %LEL slide" in p6.get("fix:1", "") and "a label could sit closer" not in p6.get("fix:1", "")
              and "Do NOT start again from --init-build" in p6.get("fix:1", ""), p6.get("fix:1", "")[-800:])
        check("... never the operator's (SCRIPT:), and the fix round may not edit the approved script nor approve it (2.63.3 "
              "measurement: a fix round changed s05's kind and M02 stopped compiling)",
              "a Your turn activity" not in p6.get("fix:1", "") and "NEVER edit working_claude/script/M01.json" in p6.get("fix:1", "")
              and "Never run content_script.py approve" in p6.get("fix:1", ""), p6.get("fix:1", "")[-900:])
        cap = [p6.get("fix:1", "")]                     # 2.72.7: a fix round with no figure finding builds itself, as before
        check("2.72.0 a fix round (figure and QA) gets AT MOST TWO builds, tries each figure in the studio first, and stops "
              "after the second whatever it prints (the second proof run: three figure fixers, 58-102 min and $50, "
              "rebuilding \"until module clean\")",
              all("AT MOST TWO build_module.py runs" in p and "studio.py" in p and "never a third build" in p
                  and "until module clean" not in p for p in cap), [p[-700:] for p in cap])
        check("2.72.5 ... and AT MOST SIX studio runs a figure, iterating with --quick (findings, no pictures) and one look "
              "with --step all (run 2's M03 fixer: 59 studio-script runs, 58 min, on one drawing)",
              all("AT MOST SIX studio runs" in p and "--quick" in p and "--step all" in p for p in cap), [p[-900:] for p in cap])
        check("2.72.7 builders and fixers check a layout change with build_module.py --slides (seconds, nothing written) "
              "before a full build; the card says so",
              all("--slides" in p and "nothing" in p.split("--slides", 1)[1][:400] for p in cap + [b1f, pf.get("fixbuild:1", "")])
              and "--slides s05,s10" in card, [p[-1200:] for p in cap])
        seven =run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_scriptonly": ["1"]})
        check("... a QA whose only BROKEN finding is the approved script's sends nothing back (reported, blocking)",
              not any(x.startswith("fix:") for x in seven.get("labels", [])) and "1" in seven.get("r", {}).get("blocking", []),
              seven.get("labels"))
        q6 = (six.get("r", {}).get("qa") or [None])[0] or {}
        check("... and the second QA's verdict is the module's (clean after the fix: not blocking), the first one's findings kept",
              "1" not in six.get("r", {}).get("blocking", []) and q6.get("module") == "1+fix"
              and any(f.get("severity") == "BROKEN" for f in q6.get("first_qa") or []), six.get("r"))
        l5 = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "wave": 1}).get("labels", [])
        check("args.wave 1: one build at a time - module 2's build starts after module 1's build (its QA holds no place)",
              l5.index("build:2") > l5.index("build:1") and "build:final" not in l5, l5)
        # 2.71.0 - biggest first, a rolling pool, seed_from, the builder card, the 3D step
        mods3 = mods + [{"id": 3, "title": "C", "minutes": 60, "theory": 60, "practical": 0}]
        order = [{"id": 2, "cost": 112}, {"id": 3, "cost": 89}, {"id": 1, "cost": 51}]
        p8 = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods3, "_approved": ["1", "2", "3"], "_order": order,
                       "wave": 1, "factory": "C:/f/skills", "seed_from": "C:/old/course"})
        l8, pr8 = p8.get("labels", []), p8.get("prompts", {})
        builds = [x for x in l8 if x in ("build:1", "build:2", "build:3")]
        check("2.71.0 the gate costs every module (build_order.py --json) and the modules build biggest first",
              "build_order.py" in pr8.get("gate:ilo-map+kb", "") and "--modules 1,2,3 --json" in pr8.get("gate:ilo-map+kb", "")
              and builds == ["build:2", "build:3", "build:1"], l8)
        check("... a pool of args.wave builds (merge: only a build holds a place): the next build starts when one ends, "
              "biggest first, not after a whole wave",
              l8.index("build:3") > l8.index("build:2") and l8.index("build:1") > l8.index("build:3"), l8)
        check("... only the biggest builds with --long-pole (its first build goes first)",
              "--long-pole" in pr8.get("build:2", "") and "--long-pole" not in pr8.get("build:1", "")
              and "--long-pole" not in pr8.get("build:3", ""), pr8.get("build:2", "")[-1600:])
        check("... args.seed_from goes to every --init-build and to the cost",
              all('--init-build --seed-from "C:/old/course"' in pr8.get("build:%d" % k, "") for k in (1, 2, 3))
              and '--seed-from "C:/old/course"' in pr8.get("gate:ilo-map+kb", ""), pr8.get("build:1", "")[:2500])
        check("... the builder reads the card, not the whole skill",
              "C:/f/skills/course-factory/compile/BUILDER_CARD.md" in pr8.get("build:1", "")
              and "Invoke the course-factory skill" not in pr8.get("build:1", ""), pr8.get("build:1", "")[:600])
        nine = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods3, "_approved": ["1", "2", "3"],
                         "factory": "C:/f/skills", "_scene": ["1", "3"], "_bad3d": ["3", "3+fix"]})
        l9, p9, r9 = nine.get("labels", []), nine.get("prompts", {}), nine.get("r", {})
        check("2.71.0 every built module gets the 3D step; one with no 3D-kit scene goes straight to QA",
              all("3d:%d" % k in l9 for k in (1, 2, 3)) and "review3d:2" not in l9 and l9.index("qa:2") > l9.index("3d:2"), l9)
        check("... a scene is checked by the script and judged by a SEPARATE reviewer - 2.72.5: at the same time as QA",
              "review3d:1" in l9 and l9.index("review3d:1") > l9.index("3d:1") and l9.index("qa:1") < l9.index("review3d:1")
              and "scene3d_check.py" in p9.get("3d:1", "") and "You did NOT build this 3D scene" in p9.get("review3d:1", "")
              and "C:/c/r/s05_step1.png" in p9.get("review3d:1", ""), l9)
        check("... a BROKEN 3D finding: ONE fix round with exactly those findings, then the check and the reviewer once more "
              "(the check only reports) - never a third",
              "fix:3" in l9 and "3d:3+fix" in l9 and "review3d:3+fix" in l9 and l9.count("fix:3") == 1 and "fix:1" not in l9
              and "fix3d:3" not in l9 and "a row of buttons" in p9.get("fix:3", "") and "scene3d_check.py" in p9.get("fix:3", "")
              and "do not change anything" in p9.get("3d:3+fix", "")
              and l9.index("3d:3+fix") > l9.index("fix:3") and l9.index("review3d:3+fix") > l9.index("3d:3+fix"), l9)
        allx = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods3, "_approved": ["1", "2", "3"],
                         "factory": "C:/f/skills", "_scene": ["1"], "_bad3d": ["1"], "_figs": ["1"], "_badfig": ["1"], "_broken": ["1"]})
        la, pa = allx.get("labels", []), allx.get("prompts", {})
        judges = ("3d:1", "figshots:1", "qa:1")
        check("2.72.5 the 3D check, the figure photographs and QA start together after the build - none waits for another's "
              "review (2.72.3 M01: 13 min of reviews one after the other before the first fixer)",
              all(j in la for j in judges) and max(la.index(j) for j in judges) < min(la.index("review3d:1"), la.index("reviewfig:1"))
              and min(la.index(j) for j in judges) > la.index("build:1"), la)
        check("... the 3D and QA findings go to ONE module fixer, the figure's to its own fixer beside it (2.72.7); neither "
              "builds, ONE build after both, then only what was BROKEN is judged again, again together",
              la.count("fix:1") == 1 and la.count("fixfig:1:s03") == 1 and not any(x.startswith("fix3d:") for x in la)
              and all(w in pa.get("fix:1", "") for w in ("a row of buttons", "an oxygen monitor")) and "inside the hull" not in pa.get("fix:1", "")
              and "inside the hull" in pa.get("fixfig:1:s03", "") and "(3D) (QA)" in pa.get("fix:1", "")
              and "DO NOT RUN build_module.py" in pa.get("fix:1", "") and "s03" in pa.get("fix:1", "").split("DO NOT RUN", 1)[-1][:200]
              and la.index("fixbuild:1") > max(la.index("fix:1"), la.index("fixfig:1:s03"))
              and "scene3d_check.py" in pa.get("fixbuild:1", "")
              and all(la.index(x) > la.index("fixbuild:1") for x in ("3d:1+fix", "figshots:1+fix", "qa:1+fix"))
              and la.count("qa:1+fix") == 1 and "fix:2" not in la, la)
        many = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_figs": ["1"], "_manyfigs": ["1"],
                         "factory": "C:/f/skills"})
        lm = many.get("labels", [])
        check("2.72.7 five broken figures: five figure fixers, at most THREE at once (the hidden-browser slots), then one build "
              "(the 2.72.5 run's M03 fixer: 37 min, 48 studio runs one after the other)",
              sorted(x for x in lm if x.startswith("fixfig:1:")) == ["fixfig:1:s0%d" % k for k in range(3, 8)]
              and many.get("figMax") == 3 and lm.count("fixbuild:1") == 1
              and lm.index("fixbuild:1") > max(lm.index(x) for x in lm if x.startswith("fixfig:")), (lm, many.get("figMax")))
        check("... a BROKEN 3D finding still there after the fix blocks the module",
              "3" in r9.get("blocking", []) and "1" not in r9.get("blocking", []), r9.get("blocking"))
        check("args.factory pins the skills every agent reads, args.notes reaches every module agent",
              "C:/f/skills/course-factory/compile/BUILDER_CARD.md" in pr.get("build:1", "")
              and "C:/f/skills/course-factory/compile/GUIDE.md" in pr.get("build:1", "")
              and "C:/f/skills/course-factory/scripts/course_gate.py" in pr.get("gate:ilo-map+kb", "")
              and "no paid pictures" in pr.get("build:1", "") and "no paid pictures" in pr.get("script:2", ""), pr)
        # 2.73.0 - Phase A with no agent, the course's ONE photo pass, a builder only where Phase A left work
        ph_run = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods, "_approved": ["1"]})
        lb, op = ph_run.get("labels", []), ph_run.get("opts", {})
        pa = ph_run.get("prompts", {}).get("phase-a:modules", "")
        check("2.73.0: Phase A runs first, with no builder - one agent (Sonnet, low) runs the catalogue and phase_a.py for the "
              "approved modules, and the course's ONE photo pass runs beside it", "phase-a:modules" in lb and "photos:course" in lb
              and lb.index("phase-a:modules") < lb.index("build:1") and op.get("phase-a:modules") == {"model": "sonnet", "effort": "low"}
              and "photo_catalogue.py assign" in pa and "phase_a.py" in pa and "--modules 1" in pa and "--wait" in pa, (lb, pa[-300:]))
        pc_ = ph_run.get("prompts", {}).get("photos:course", "")
        check("... the photo pass works down PHOTOS_TO_FIND.md into photos_found/ with found_for, never a module or a sheet",
              "PHOTOS_TO_FIND.md" in pc_ and "photos_found" in pc_ and '"found_for"' in pc_ and "never a module" in pc_, pc_[-500:])
        check("... a script written in this run gets the ONE photo pass after all scripts are written - not one agent per script",
              "photos:drafts" in lb and lb.index("photos:drafts") > lb.index("script:2") and not any(x.startswith("photos:2") for x in lb), lb)
        check("... and the builder is told the photo catalogue's candidates are in its needs file",
              "M01_VISUAL_NEEDS.md" in ph_run.get("prompts", {}).get("build:1", ""), ph_run.get("prompts", {}).get("build:1", "")[:1600])
        four = [{"id": i, "title": "M%d" % i, "minutes": 100 - i, "theory": 40, "practical": 20} for i in (1, 2, 3, 4)]
        b_run = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": four, "_approved": ["1", "2", "3", "4"],
                          "_phase_a": [{"module": "1", "line": "PASS M01 - figures, compile ... (300 s)"},
                                       {"module": "2", "line": "PHASE A CLEAN M02 - every check that does not depend on the pictures passed"},
                                       {"module": "3", "line": "FAIL M03 - compile (90 s)"},
                                       {"module": "4", "line": "MODULE CLEAN M04 - only the course package is left"}]})
        lb = b_run.get("labels", [])
        b2 = b_run.get("prompts", {}).get("build:2", "")
        check("... a module Phase A brought to PASS or MODULE CLEAN gets NO builder, only its judges and QA",
              "build:1" not in lb and "build:4" not in lb and "qa:1" in lb and "qa:4" in lb, lb)
        check("... the rest get a builder told Phase A's answer and sent to its needs file, --auto first, never --init-build",
              "build:2" in lb and "build:3" in lb and "PHASE A CLEAN M02" in b2 and "M02_VISUAL_NEEDS.md" in b2
              and "--auto" in b2 and "Do NOT start again from --init-build" in b2, b2[-1200:])
        # 2.66.0 (Raivis) - a builder reads its instructions by their path, never the whole skill (SKILL.md, 48 KB, the router
        # for every mode); (merge) what it reads is the builder card (2.65.0 / 2.72.x), the GUIDE named for reference
        b1 = pr.get("build:1", "")
        check("2.66.0: a builder is sent to the builder card by its path - not SKILL.md, not the skill loaded",
              "Do NOT read the course-factory SKILL.md" in b1 and "or load the skill" in b1 and not b1.startswith("Invoke"), b1[:500])
        dflt = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods,
                         "_skill_dir": "C:/u/plugins/cf/2.66.0/skills/course-factory/SKILL.md"})
        db = dflt.get("prompts", {}).get("build:1", "")
        check("... the installed plugin too: the gate reports the skill's folder (by Glob, never reading SKILL.md) and the "
              "builders get the card and the GUIDE by it", "C:/u/plugins/cf/2.66.0/skills/course-factory/compile/BUILDER_CARD.md" in db
              and "C:/u/plugins/cf/2.66.0/skills/course-factory/compile/GUIDE.md" in db
              and "do not read that file" in dflt.get("prompts", {}).get("gate:ilo-map+kb", ""), db[:400])
        none = run(tmp, {"course": "C:/c", "programme": "C:/p.pdf", "modules": mods}).get("prompts", {}).get("build:1", "")
        check("... a gate that brought back no folder: the builder finds the card through the skill's name, still not loading "
              "SKILL.md", "compile/BUILDER_CARD.md in the course-factory skill's folder" in none
              and "Do NOT read the course-factory SKILL.md" in none, none[:300])
        with open(os.path.join(HERE, "..", "..", "compile", "BUILDER_CARD.md"), encoding="utf-8") as f:
            card_lines = f.read().splitlines()
        check("... and the card stays a short read (the ~12,000 tokens of SKILL.md the builders no longer carry): under 110 "
              "lines", len(card_lines) < 110, len(card_lines))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
