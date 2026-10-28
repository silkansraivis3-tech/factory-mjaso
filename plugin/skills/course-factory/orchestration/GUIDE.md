# Orchestration — one agent reads the programme, then the modules are built at once

Read this when a **whole course** is being built from a knowledge base, and the module count is
large enough that building them one after another is the slow part.

**The short answer to "is it possible": yes, and it is not the hard part.** Eight modules built by
eight agents in parallel is a normal fan-out. The hard part is everything that must be decided
*before* the fan-out, because eight agents cannot negotiate with each other — and the reason this
guide exists is that the failures are all in that seam, not in the parallelism.

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
  1..N SCRIPTS       one script writer per module, all at once; then ONE course-wide photo pass (2.73.0)
     |               script -> operator approves (never typed by the builder)
     v
  A  PHASE A         no agent (2.73.0): photo_catalogue.py assign, then phase_a.py builds every approved module
     |               in ONE local queue sized by the computer's browser slots - placeholders, every check, --auto picks;
     |               beside it the course's ONE photo-sourcing pass (PHOTOS_TO_FIND.md -> working_claude\photos_found)
     v
  B  PHASE B         only the modules Phase A left at PHASE A CLEAN or FAIL: an agent reads the module's
     |               MNN_VISUAL_NEEDS.md (BUILDER_CARD.md), fills the slots, builds to module clean -
     |               then its judges and QA as in 2.72.x; a module Phase A finished goes straight to them
     v
  Q  QA              per module as it lands, then one cross-module pass
     |
     v
  +  ASSEMBLY        the orchestrator alone: compile_course.py, handout, hours total, publish
```

Four rules hold that shape together. Each is here because dropping it produces a specific,
recognisable wreck.

---

## Rule 1 · Everything shared is decided before the fan-out

A parallel agent cannot ask another agent a question. So anything two modules could disagree about
has to be settled by the reader and frozen at the gate:

| Settled before fan-out | Why, in one line |
|---|---|
| **The minutes per module** | Two agents both "rounding up to fit" is how a course built to 2175 minutes against an accredited 1640. L1. |
| **The module split and numbering** | A module that renumbers itself breaks every cross-reference in every other module. |
| **COURSE_LANGUAGE** | L19. One agent quietly translating is the drift this factory already has a check for. |
| **The visual system** | The token set (`course-module-ui`). Eight agents inventing eight dialects is exactly what `audit_ui.py --strict` exists to stop. |
| **Task code ranges** | Module 3 owning `GAS3xx` and nobody else touching it. |
| **The ILO map** | Below. This is the one that actually makes parallelism work. |

> If something is not on that list and two modules could still collide over it, it belongs on that
> list. Add it before the run, not after the merge.

---

## Rule 2 · The reader's output is a FILE, and it is not slides

The first agent works alone with the programme, the model course and the knowledge base, and
produces the Stage 2 files in the course folder (since 2.42.0 the factory's own, not free-form notes):

**`working_claude/architecture.json`** (shown as `to_review/ARCHITECTURE_REVIEW.html`) — module →
official topic → allocated minutes (theory / practical) → what the module teaches → what it checks →
the practicals and their equipment. The minutes sum to the programme total or the reader has not
finished.

**`working_claude/ilo_map.json`** — the ILO map, written by `make_architecture_page.py` with the page
(`scripts/ilo_map.py`): for every module, its Main ILO verbatim and every Sub-ILO it owes, one row each,
with the model-course items under its topic. `ilo_map.py show <course> --module N` prints one module's rows.

And when `kb_tool.py find` finds no knowledge base, the factory's **suggestion to make one**, word for
word - the operator decides, and `kb_tool.py decision` records it. `scripts/course_gate.py` stops every
module agent until the page is approved with its ILO map and the knowledge-base decision is recorded.

> **The ILO map never appears in a slide.** It is the build's own instrument: it tells each module
> agent what it owes, and it tells the QA agent what to check. A trainee does not need to read a
> traceability matrix, and putting one on a screen is how a course starts looking like a compliance
> document instead of teaching material — see L22.

Two further reasons the map is a file and not a conversation. A file is the only thing eight agents
can all read without eight copies of the knowledge base going into eight contexts. And a file is
what the owner actually reviews at the gate — a table they can disagree with line by line, while
disagreeing is still free.

---

## Rule 3 · One agent, one folder — and the orchestrator owns everything shared

Every module agent may write **only** inside `modules/moduleNN/` and its own `working_claude\script\MNN.*`
and `working_claude\figures\MNN\`. Everything that more than one module touches is written by the
orchestrator after the fan-out, alone:

- the course's own pages: `compile/scripts/compile_course.py` writes `COURSE.html`, `_course_shell/course_map.js`
  and every module's `START_HERE.html` / `START_HERE_EXTENDED.html` from the approved architecture, the scripts
  and the built decks; `scripts/check_course_package.py` then runs the classroom's importer on them (2.37.0)
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

This is not tidiness. Two agents writing the same file is a lost write that no test catches,
because the file is still valid HTML afterwards — it is just missing one agent's work.

---

## Rule 4 · QA runs per module, then once across all of them

"One extra agent that checks if all modules are being created well" is right, with one correction
worth making: a QA agent has nothing to check while a module is still being written. So run it as a
**pipeline**, not as a ninth parallel worker —

- **as each module lands**, a QA agent reads that module against its rows in `ilo_map.json` and its
  minutes in `architecture.json`, and runs the deterministic checks. Module 3 is being verified while
  Module 7 is still being written; no wall-clock is wasted.
- **once at the end**, a single cross-module pass that only it can do: task codes unique across the
  course, terminology consistent, the hours total, the visual dialect, every cross-reference
  between modules resolving, every outcome in the ILO map taught somewhere.

The per-module QA agent must be a **different** agent from the one that built the module. An agent
asked to check its own work confirms it.

---

## Rule 5 · The build has this QA; a fix does not (L50)

This pipeline — builder, a different agent as QA, then the cross-module pass — is for **building**. Once the
modules exist, the operator's review points and every "in all modules too" are **fixes**: `fix/GUIDE.md`, one sweep,
one list, one yes, one check by whoever made the change. Do not start this workflow, a fixer agent per module or a QA
agent behind a fix (GAS ADVANCED, FEEDBACK_LOG #61–#93: that is how a small fix took 30 minutes). A course-wide wish
the operator states during review goes into `working_claude\STANDARDS.md`, and builders still to run read it.

## What the agents are

| | Model | Tools | Reads | Writes |
|---|---|---|---|---|
| **Reader** | the strongest available | read + search only | programme, model course, KB | `architecture.json`, `ilo_map.json` (via the Stage 2 page), the KB suggestion |
| **Script writer** (a module whose script is not approved) | the strongest available | full | its own rows of the ILO map, its module in `architecture.json`, its source extracts, `script/GUIDE.md` | its script, review page and Word file - then STOP |
| **Module** (an approved script) | Sonnet, medium effort (2.51.0) | full | its own rows of the ILO map (`ilo_map.py show`) and its module in `architecture.json`, its source extracts, `script/GUIDE.md`, then - once its script is approved - `compile/GUIDE.md` and the picture lanes (`course-visuals`). **Not** the HTML rules (`course-module-ux`, `course-module-ui`, `course-task-ux`): the compiler builds their standard | its script and build sheet, its figures, `modules/moduleNN/` - and never HTML by hand |
| **Phase A** (2.73.0) | no model: one local process, `phase_a.py`, started and waited on by a Sonnet agent at low effort | nothing | every approved module as far as it goes with placeholders, and its `MNN_VISUAL_NEEDS.md` |
| **Photo pass** (2.73.0) | Sonnet, medium effort - ONE for the course | `visuals/PHOTOS_TO_FIND.md` | `working_claude/photos_found/` with each photo's record and `found_for` |
| **Visual** | the `nano-banana:image-director` agent (generates) or `course-factory:visual-sourcer` (finds) | read, write, web, the nano-banana tools | a `GENERATED_ASSET_REQUIRED` brief | the asset files named in the brief |
| **QA** | Sonnet, medium effort (2.51.0); never the builder | read + run checks: `build_module.py --no-fix --no-review` once, the checks it does not run in one more call | the module, the two maps | a findings list — **never a fix** |

**The visual agent is how a missing picture gets made without stopping the build.** When a module
reaches an image it cannot produce, it carries on. A real picture is searched for by `visual-sourcer`
without asking. A **generated** one is never made automatically (L47 - every picture costs about
€0.10): the person describes it and says yes to the prompt first (`scripts/picture_briefs.py`), and
only then is it spawned on `nano-banana:image-director`, which makes it once. `course-visuals/scripts/write_visual_handoff.py` writes the same request to a file as the
fallback, for when the agent is unavailable or generation is blocked (no key, billing off). Build the module as far as it
goes either way; never leave it unfinished because one picture is missing.

---

## The limits of one computer - and of one workflow (2.73.0)

Measured on the chem advanced run (2026-10-27, 21 modules, 2.70.0): 18 builder agents at once hit the **Workflow tool's
cap of 20 subagents** (QA agents and script writers count too), the **CPU sat at 100 %**, and every build queued on the
computer's **browser slots** (`scripts/browser_slots.py`: a quarter of the cores, 2-8; a build takes up to three hidden
browsers - one per audit size - plus its figures) and on the **cold-build lock** (one module's first build at a time,
2.63.3). More builder agents than the slots can serve buy nothing: they wait, and each wait is a model turn.

So from 2.73.0 the build is queued by the computer, not by agents:

- **Phase A** is `compile/scripts/phase_a.py <course> --modules 1-21` - one local process, `browser_slots.count() // 3`
  modules at a time (`--jobs` to change it), no model at all. One agent starts it and waits (`--wait`, like a build).
- **Phase B** builders only for the modules that need a judgement - their pictures - still at most `args.wave` builds at
  once; a module Phase A brought to PASS or MODULE CLEAN spends no builder at all, so builders, judges, QA and the photo
  pass stay further under the cap of 20.
- **The photo search is ONE pass for the course** (`photos:course`), not one agent per script: the catalogue
  (`scripts/photo_catalogue.py`) already holds every old-course and knowledge-base picture, and `PHOTOS_TO_FIND.md` lists
  only what nothing in them shows.

---

## Is it hard?

Honestly: **the fan-out is easy and the seams are not.** Writing eight agents takes one call. What
takes the care is the six rows of the table in Rule 1, the two map files, and the discipline that
one agent writes one folder. Every one of those exists because of a failure this factory already
recorded — hours that did not add up, a course that changed language one screen at a time, a second
visual dialect, a section nothing linked to.

Two things that are genuinely harder than they look, and are worth knowing before starting:

- **Cost is not divided, it is multiplied.** Eight agents building eight modules is eight modules'
  worth of work happening at once, not one module's worth spread thinner. Parallelism buys
  wall-clock, never tokens.
- **A failed agent must not silently produce a thin module.** An agent that could not find its
  source material will still return something. That is what the per-module QA pass and
  `classify_module.py` are for: a module that classifies C after a full build did not finish, and
  the run must say so rather than reporting eight successes.

---

## Running it

**Whether it runs is asked, never assumed (2.73.1).** With the Stage 2 approval the operator is asked once - all modules at
once with agents, or module by module in the session (SKILL.md, "How the modules are built") - and the answer is kept in
`intake.json` `"build_mode"`. `"workflow"` is the operator's own request for this script: it runs without their having to
name agents or workflows.

`orchestration/workflows/build_course.js` is a ready script for the `Workflow` tool: reader → gate →
parallel modules with QA pipelined behind each → the cross-module pass. Read it before running it —
it is deliberately short, and the module prompt inside it is the thing worth editing for a
particular course.

**The gate is not automated, and must not be.** The script stops after the reader and prints the
table. The module split and the minutes are the expensive things to get wrong, and changing a table
row is free while changing eight built modules is not.

**Neither is the script approval (L29).** In pass 2 a module agent whose content script is not approved
writes it and stops at its review page; the operator approves each one, and pass 2 runs again - an approved
module is then compiled, never typed. So a module agent loads the script lane and the picture lanes, not the
HTML rules: about **38,500 tokens of rules instead of 80,800** before its first slide (measured on 2.37.0,
size ÷ 4, `docs/PROPOSAL_SCRIPT_COMPILER.md` §6), and it no longer writes the 80-160 KB of deck and task
HTML a module of the IGF pilot has - it writes a 3-5 KB build sheet and its figures.
A module agent builds and checks with ONE command, `compile/scripts/build_module.py <course> --module N
--no-course-pages` (2.50.0; the orchestrator alone writes the course's pages), starting from the Quickstart of
`compile/GUIDE.md` and `course-visuals/kit/CATALOGUE.md`; its visual review is one `haiku` subagent reading the sheets
the build made (`compile/REVIEW_PROMPT.md`). `build_course.js` does this from 2.51.0 - before, its module prompt still
said `compile_module.py`, then fix and build again, and its QA ran 13 checks one at a time. The words come from the
session's model (the reader, the script writer); building an approved script and QA, the mechanical loop, run on Sonnet
at medium effort, and the gate (one command) at low. `args.factory` pins the factory's skills folder for a benchmark,
`args.notes` passes the operator's words for the run to every module agent.
