# Orchestration — one agent reads the programme, then the modules are built at once

Read this when a **whole course** is being built from a knowledge base, and the module count is
large enough that building them one after another is the slow part. The fan-out itself is easy; what
must be right is everything decided *before* it, because parallel agents cannot negotiate with each other.

---

## The shape

```
  0  READER          one agent, alone with the knowledge base
     |               programme · model course · what each module teaches
     |               writes:  architecture.json   ilo_map.json   ARCHITECTURE_REVIEW.html
     |                        (files, never slides) - and the knowledge-base suggestion if there is none
     v
  =  GATE            the owner approves the page and the ILO map on it; the KB decision is recorded.
     |               course_gate.py checks both - no module agent starts until it says open.
     |
     v
  1..N SCRIPTS       one script writer per module, all at once; then ONE course-wide photo pass
     |               script -> operator approves (never typed by the builder)
     v
  A  PHASE A         no agent: photo_catalogue.py assign, then phase_a.py builds every approved module
     |               in ONE local queue sized by the computer's browser slots - placeholders, every check, --auto picks;
     |               beside it the course's ONE photo-sourcing pass (PHOTOS_TO_FIND.md -> working_claude\photos_found)
     v
  B  PHASE B         only the modules Phase A left at PHASE A CLEAN or FAIL: an agent reads the module's
     |               MNN_VISUAL_NEEDS.md (BUILDER_CARD.md), fills the slots, builds to module clean -
     |               then its judges and QA; a module Phase A finished goes straight to them
     v
  Q  QA + WALK       per module as it lands: QA (words, teaching, task pages) and the walk judge (every slide at
     |               every stop, signed) side by side; ONE fix round for both; then one cross-module pass
     |
  P  POLISH          a module that passes with nothing BROKEN left: one round on opus, about ten minutes, through its
     |               POLISH list - each change kept only if the module still passes (fix.py polish, compile/GUIDE.md 6)
     v
  +  ASSEMBLY        the orchestrator alone: compile_course.py, handout, hours total, publish
```

---

## Rule 1 · Everything shared is decided before the fan-out

A parallel agent cannot ask another agent a question. So anything two modules could disagree about
has to be settled by the reader and frozen at the gate:

| Settled before fan-out | Why, in one line |
|---|---|
| **The minutes per module** | Agents each "rounding up to fit" overrun the accredited total. L1. |
| **The module split and numbering** | A module that renumbers itself breaks every cross-reference in every other module. |
| **COURSE_LANGUAGE** | L19. One agent quietly translating is drift. |
| **The visual system** | The token set (`course-module-ui`); `audit_ui.py --strict` stops a second dialect. |
| **Task code ranges** | Module 3 owning `GAS3xx` and nobody else touching it. |
| **The ILO map** | Below. This is the one that makes parallelism work. |
| **The simulator tasks** (L66) | An advanced course's `SIM_COVERAGE.json` says which module runs which simulator task and for how many minutes, so two modules never invent an exercise for the same item. |

**Making the simulator coverage (L66) in parallel**, before the gate (`coverage/SIMULATORS.md`): one Sonnet agent per
simulator manual writes its part of `SIM_MAP.md` (capabilities, procedures, faults - every fact with its page); then one
agent per two or three competences judges their syllabus rows in `SIM_COVERAGE.json` against the finished map; then
this session ranks the GAP tasks and one agent per task drafts its exercise forms. Each agent writes its own file; this
session merges, recounts and runs `sim_coverage.py check`.

> If something is not on that list and two modules could still collide over it, it belongs on that
> list. Add it before the run, not after the merge.

---

## Rule 2 · The reader's output is a FILE, and it is not slides

The first agent works alone with the programme, the model course and the knowledge base, and
produces the Stage 2 files in the course folder (the factory's own formats, not free-form notes):

**`working_claude/architecture.json`** (shown as `to_review/ARCHITECTURE_REVIEW.html`) — module →
official topic → allocated minutes (theory / practical) → what the module teaches → what it checks →
the practicals and their equipment. The minutes sum to the programme total or the reader has not
finished.

**The programme's words in English (L19).** The course is English; the programme may not be
(`programme.json` `"language"`), and it stays as it is. When it is not English, the reader writes the
English beside every programme text the course quotes, in `architecture.json`: a Main ILO's
`"text_en"`, a module's `"topic_en"` (its programme topic), a kept Sub-ILO's `"text_en"` - a faithful
rendering, the verb, subject and standard unchanged; the verbatim `"text"` stays the programme's. A
re-expressed or added Sub-ILO is written in English. The Stage 2 page shows each rendering under the
programme's words and is not approved while one is missing; the module plans and the ACP show the
English, the review pages the programme's own words.

**`working_claude/ilo_map.json`** — the ILO map, written by `make_architecture_page.py` with the page
(`scripts/ilo_map.py`): for every module, its Main ILO verbatim and in English, and every Sub-ILO it owes,
one row each, with the model-course items under its topic. `ilo_map.py show <course> --module N` prints one module's rows.

And when `kb_tool.py find` finds no knowledge base, the factory's **suggestion to make one**, word for
word - the operator decides, and `kb_tool.py decision` records it. `scripts/course_gate.py` stops every
module agent until the page is approved with its ILO map and the knowledge-base decision is recorded.

> **The ILO map never appears in a slide** (L22). It is the build's own instrument: it tells each module
> agent what it owes, and it tells the QA agent what to check.

A file, not a conversation: every agent reads it without its own copy of the knowledge base, and the owner reviews it
line by line at the gate.

---

## Rule 3 · One agent, one folder — and the orchestrator owns everything shared

Every module agent may write **only** inside `modules/moduleNN/` and its own `working_claude\script\MNN.*`
and `working_claude\figures\MNN\`. Everything that more than one module touches is written by the
orchestrator after the fan-out, alone (two agents writing one file lose a write that no test catches):

- the course's own pages: `compile/scripts/compile_course.py` writes `COURSE.html`, `_course_shell/course_map.js`
  and every module's `START_HERE.html` / `START_HERE_EXTENDED.html` from the approved architecture, the scripts
  and the built decks; `scripts/check_course_package.py` then runs the classroom's importer on them
- `courses/<id>/course.json` and the generated `courses/registry.js`, when the course goes to the Android
  terminals (`course-tablet-publisher`)
- the handout — it is one document with one running structure, and it is also the overflow valve
  for L1, so it cannot be assembled until every module knows what it could not fit
- the instructor run content, the task manifest, the cross-module checks
- anything under the terminals
- **the figure kit (L55).** A module agent that needs a part the kit lacks makes it in its own
  `modules/mN/assets/kit_parts.js` and uses it - it never edits the factory's `kit.js`. At assembly the
  orchestrator runs `course-visuals/kit/scripts/kit_parts.py promote` on **all** modules at once: a part two
  modules both made is promoted once and the difference merged by hand, then one merge request for the owner
  (the operator is asked before the push)

---

## Rule 4 · QA runs per module, then once across all of them

A QA agent has nothing to check while a module is still being written, so run it as a **pipeline**, not as one more
parallel worker:

- **as each module lands**, a QA agent reads that module against its rows in `ilo_map.json` and its
  minutes in `architecture.json`, and runs the deterministic checks.
- **once at the end**, a single cross-module pass: task codes unique across the course, terminology consistent, the
  hours total, the visual dialect, every cross-reference between modules resolving, every outcome in the ILO map
  taught somewhere.

The per-module QA agent must be a **different** agent from the one that built the module: an agent checking its
own work confirms it.

**The walk judge stands beside QA.** A module is not done, and the portal refuses its upload, until an AI reviewer
has looked at every slide at every stop a trainee sees (`compile/GUIDE.md` 2i). The workflow runs that itself: ONE
reviewer per module - never its builder or a fixer, whose signature `walk_review.py` refuses - reads the contact sheets
in batches of up to 4, signs, and reports the fails with slide and stop (a session working by hand gives each batch to
its own Opus subagent at high effort instead: the same sheets, the same brief). They join the module's ONE fix round; after it the
walk judge looks once more, only at the slides the round changed (the walk keeps each slide's fingerprint, the audits'
own), and signs against the builder and every fixer of the round. Two looks, never a third: what still fails is on the
module's `for_aleksis` with the `walk_review.py accept` command, the module is not failed for it, and the run's result
names the modules whose upload waits (`walk.not_passed`). The final assessment gets one judge after it is built
(`walk:final`, `final_walk` in the result) and no fix round. A second run of the workflow over a module that has had
its two rounds sends no walk fail to a fixer and reviews nothing again: the operator accepts what is left or reopens
it (`walk_review.py reopen`) - both are the operator's own, never an agent's. A judge that brought back nothing is not
retried in the run: that module is walked by hand. So the two reviews do not overlap: the QA agent's sheets hold the
task pages only, the deck's slides are the walk judge's.

---

## Rule 5 · The build has this QA; a fix does not (L50)

This pipeline — builder, a different agent as QA, then the cross-module pass — is for **building**. Once the
modules exist, the operator's review points and every "in all modules too" are **fixes**: `fix/GUIDE.md`, one sweep,
one list, one yes, one check by whoever made the change. Do not start this workflow, a fixer agent per module or a QA
agent behind a fix. A course-wide wish the operator states during review goes into `working_claude\STANDARDS.md`, and
builders still to run read it.

## What the agents are

| | Model | Tools | Reads | Writes |
|---|---|---|---|---|
| **Reader** | the strongest available | read + search only | programme, model course, KB | `architecture.json`, `ilo_map.json` (via the Stage 2 page), the KB suggestion |
| **Script writer** (a module whose script is not approved) | the strongest available | full | its own rows of the ILO map, its module in `architecture.json`, its source extracts, `script/GUIDE.md` | its script, review page and Word file - then STOP |
| **Module** (an approved script) | Sonnet, medium effort | full | its own rows of the ILO map (`ilo_map.py show`) and its module in `architecture.json`, its source extracts, `script/GUIDE.md`; once its script is approved, `compile/BUILDER_CARD.md` and nothing else. **Not** the HTML rules (`course-module-ux`, `course-module-ui`, `course-task-ux`): the compiler builds their standard | its script and build sheet, its figures, `modules/moduleNN/` - and never HTML by hand |
| **Phase A** | no model: one local process, `phase_a.py`, started and waited on by a Sonnet agent at low effort | nothing | every approved module as far as it goes with placeholders, and its `MNN_VISUAL_NEEDS.md` |
| **Photo pass** | Sonnet, medium effort - ONE for the course | `visuals/PHOTOS_TO_FIND.md` | `working_claude/photos_found/` with each photo's record and `found_for` |
| **Visual** | the `nano-banana:image-director` agent (generates) or `course-factory:visual-sourcer` (finds) | read, write, web, the nano-banana tools | a `GENERATED_ASSET_REQUIRED` brief | the asset files named in the brief |
| **QA** | Opus, high effort - a judgement job (the job -> model table in SKILL.md, *Building*); never the builder | read + run checks: `build_module.py --no-fix --no-walk` once, the checks it does not run in one more call | the module, the two maps | a findings list — **never a fix** |
| **Walk judge** | Opus, high effort - a judgement job; never the builder | read + `walk_review.py` (prepare, sign, verify) - never a build | the walk's contact sheets and `review_brief.md` | its verdicts, signed into `working_claude/_build/MNN_walk_review.json` — **never a fix** |

**A missing picture never stops the build.** When a module reaches an image it cannot produce, it carries on. A real
picture is searched for by `visual-sourcer` without asking. A **generated** one is made only within the course's
picture budget (L47 - every picture costs about €0.10), said yes to once at the start (`intake.json`
`picture_budget`): no question before each picture - the prompt comes from `scripts/picture_briefs.py`, and it is
spawned on `nano-banana:image-director`, which makes it once. `course-visuals/scripts/write_visual_handoff.py` writes
the same request to a file as the fallback, for when the agent is unavailable or generation is blocked (no key,
billing off). Build the module as far as it goes either way; never leave it unfinished because one picture is missing.

---

## The limits of one computer - and of one workflow

The **Workflow tool caps a run at 20 subagents** (QA agents and script writers count too). Every build queues on the
computer's **browser slots** (`scripts/browser_slots.py`: a quarter of the cores, 2-8; a build takes up to three hidden
browsers - one per audit size - plus its figures) and on the **cold-build lock** (one module's first build at a time).
More builder agents than the slots can serve buy nothing: they wait, and each wait is a model turn. So the build is
queued by the computer, not by agents:

- **Phase A** is `compile/scripts/phase_a.py <course> --modules 1-21` - one local process, `browser_slots.count() // 3`
  modules at a time (`--jobs` to change it), no model at all. One agent starts it and waits (`--wait`, like a build).
- **Phase B** builders only for the modules that need a judgement - their pictures - still at most `args.wave` builds at
  once; a module Phase A brought to PASS or MODULE CLEAN spends no builder at all, so builders, judges, QA and the photo
  pass stay further under the cap of 20.
- **The photo search is ONE pass for the course** (`photos:course`), not one agent per script: the catalogue
  (`scripts/photo_catalogue.py`) already holds every old-course and knowledge-base picture, and `PHOTOS_TO_FIND.md` lists
  only what nothing in them shows.

Two things to know before starting:

- **Cost is multiplied, not divided.** Parallelism buys wall-clock, never tokens.
- **A failed agent must not silently produce a thin module.** That is what the per-module QA pass and
  `classify_module.py` are for: a module that classifies C after a full build did not finish, and the run must say so
  rather than report success.

---

## Running it

**Whether it runs is asked, never assumed.** With the Stage 2 approval the operator is asked once - all modules at
once with agents, or module by module in the session (SKILL.md, the gate, step 4) - and the answer is kept in
`intake.json` `"build_mode"`. `"workflow"` is the operator's own request for this script: it runs without their having to
name agents or workflows.

`orchestration/workflows/build_course.js` is a ready script for the `Workflow` tool: reader → gate →
parallel modules with QA pipelined behind each → the cross-module pass. Read it before running it —
it is deliberately short, and the module prompt inside it is the thing worth editing for a
particular course.

**The gate is not automated, and must not be.** The script stops after the reader and prints the
table: changing a table row is free, changing eight built modules is not.

**Neither is the script approval (L29).** In pass 2 a module agent whose content script is not approved
writes it and stops at its review page; the operator approves each one, and pass 2 runs again - an approved
module is then compiled, never typed. So a module agent loads the script lane, not the HTML rules, and it writes no deck or task HTML - it writes a 3-5 KB build
sheet and its figures.
A module builder reads `compile/BUILDER_CARD.md` and nothing else, and builds and checks with ONE command,
`compile/scripts/build_module.py <course> --module N --no-course-pages` (the orchestrator alone writes the course's
pages). The builder stops at MODULE CLEAN and reviews nothing of its own; the walk judge does the one visual review - the
deck's slides at every stop and every question of every task page - and signs (Rule 4), and the QA agent beside it
looks at no screen. The words come from the session's model (the reader, the script writer); building an approved
script, the mechanical loop, runs on Sonnet at medium effort (`MECHANICAL`) - the 3D check's command and the one build
after the figure fixers too - and the gate (one command) at low; the 3D, figure, walk and QA judges and the fixes and
polish that act on them run on Opus at high effort (`JUDGEMENT`) - the job -> model table in SKILL.md, *Building*.
`args.factory` pins the factory's skills folder for a benchmark, `args.notes` passes the operator's words for the run to
every module agent.

**A session that hands out the agents itself** (the Auto build, the factory trial) runs the same script step by step:
`node orchestration/workflows/brief.mjs <args.json>` replays it with the answers its agents wrote into
`working_claude/_build/agents/` and lists the agents to start now - each with its model, effort and brief file, the
workflow's own words. The session starts each with that file's path, runs brief.mjs again as they end, and writes no
brief of its own; the gate's three commands are run by brief.mjs itself. Its `result.json` is the workflow's answer.
