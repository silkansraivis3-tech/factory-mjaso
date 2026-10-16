/* NOVIKONTAS Course Factory — read the programme, then build every module at once.
 *
 * Pass this to the Workflow tool as `script`, with `args` set to:
 *
 *   { course: "<absolute path to the course folder>",
 *     programme: "<path to the approved programme>",
 *     kb: "<path to the knowledge base - Course Source Processor or docling>",
 *     modules: [ { id: 1, title: "...", minutes: 240, theory: 200, practical: 40 }, ... ] }
 *
 * id is the module's number: its folder is modules/module01, its script working_claude/script/M01.json.
 *
 * `modules` is deliberately an INPUT, not something the script discovers. The reader
 * produces the split, the owner approves it at the gate, and only then is this run with
 * the approved table. That is the whole point of the gate — see orchestration/GUIDE.md.
 *
 * Run it in two passes:
 *   pass 1  omit `modules`  -> the reader runs, writes the Stage 2 files - architecture.json, the
 *                              ILO map (working_claude/ilo_map.json) and ARCHITECTURE_REVIEW.html -
 *                              looks for the knowledge base and, if there is none, brings back the
 *                              factory's suggestion to make one. Then it STOPS.
 *   pass 2  with `modules`  -> a gate agent runs scripts/course_gate.py first: no approved ILO map or
 *                              no knowledge-base decision, and NO module agent starts (2.42.0).
 *                              Then the fan-out, with QA pipelined behind each module.
 *
 * `kb` may be left out: the reader finds it (kb_tool.py find) or suggests one.
 *
 * The prompts below are short on purpose. Each agent loads the skill that owns its
 * question; restating a skill's rules here is how two authorities start to disagree.
 */

export const meta = {
  name: 'novikontas-build-course',
  description: 'Read an approved programme and knowledge base, then build every module in parallel with QA behind each',
  phases: [
    { title: 'Read', detail: 'One agent alone with the programme, the model course and the knowledge base' },
    { title: 'Build', detail: 'One agent per module, each owning exactly one folder' },
    { title: 'Verify', detail: 'A different agent checks each module as it lands' },
    { title: 'Cross-check', detail: 'One pass over the whole course, which only a single agent can do' },
  ],
}

const A = args || {}
const SKILL = 'the course-factory skill (Skill tool, name "course-factory")'

/* ---------------------------------------------------------------- 0 · READ */

phase('Read')

const MAP_SCHEMA = {
  type: 'object',
  required: ['modules', 'total_minutes', 'language', 'ilo_map', 'kb'],
  properties: {
    language: { type: 'string' },
    ilo_map: { type: 'string', description: 'absolute path of working_claude/ilo_map.json, written with the Stage 2 page' },
    kb: {
      type: 'object',
      required: ['status'],
      properties: {
        status: { type: 'string', enum: ['found', 'none', 'decided'] },
        path: { type: 'string' },
        suggestion: { type: 'string', description: 'when none: kb_tool.py find\'s suggestion, word for word' },
      },
    },
    total_minutes: { type: 'number' },
    modules: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'topics', 'minutes', 'theory', 'practical', 'teaches', 'checks'],
        properties: {
          id: { type: 'string' }, title: { type: 'string' },
          topics: { type: 'array', items: { type: 'string' } },
          minutes: { type: 'number' }, theory: { type: 'number' }, practical: { type: 'number' },
          teaches: { type: 'string' }, checks: { type: 'string' },
          needs_facility: { type: 'string' },
        },
      },
    },
    unknowns: { type: 'array', items: { type: 'string' } },
  },
}

const READ = `Invoke ${SKILL} in PLAN mode and follow it.

The approved programme:  ${A.programme}
The knowledge base:      ${A.kb || '(not given - find it)'}
The course folder:       ${A.course}

Work alone with those. Stage 1 and Stage 2 only — no content script, no slides:

  KNOWLEDGE BASE  course-factory/kb/scripts/kb_tool.py find <the course material folder>.
                  None found: it prints the factory's suggestion to make one (what it is,
                  which files, how, what the course loses). Return that text word for word
                  in kb.suggestion - the operator decides; record nothing yourself.

  STAGE 2 FILES   working_claude/programme.json and architecture.json - one module per
                  programme topic (L34) with its minutes (they MUST sum to the programme
                  total: hours/scripts/check_hours.py), the Main ILOs VERBATIM (L2), every
                  Sub-ILO (kept / re-expressed - PROVISIONAL until approved - / added).
                  Then scripts/make_architecture_page.py --course <course>: it writes
                  ARCHITECTURE_REVIEW.html AND the ILO map, working_claude/ilo_map.json -
                  one row per Sub-ILO per module, what every module's script is written
                  against. Return its path in ilo_map.

Detect and state COURSE_LANGUAGE (L19). Raise every UNKNOWN rather than inventing an
hour, a pass mark or a citation, and never web-search during intake.

Then return the module table as JSON. Do not build anything.`

const plan = await agent(READ, { label: 'read:programme', phase: 'Read', schema: MAP_SCHEMA })

if (!A.modules || !A.modules.length) {
  /* The gate. The owner approves the table before anything expensive happens. */
  return {
    stopped_at: 'GATE',
    why: 'The module split, the minutes and the ILO map are the expensive things to get wrong. '
       + 'Show the operator to_review/ARCHITECTURE_REVIEW.html (it carries the ILO map)'
       + (plan && plan.kb && plan.kb.status === 'none' ? ' and the suggestion to make a knowledge base (kb.suggestion), and record '
          + 'their answer with kb_tool.py decision' : '')
       + '; record their "next" with make_architecture_page.py --approve --by "<name>", then re-run with '
       + 'args.modules set to the approved table.',
    proposed: plan,
  }
}

/* ------------------------------------------------ the gate, checked - not trusted */

const GATE_SCHEMA = {
  type: 'object',
  required: ['open', 'output'],
  properties: { open: { type: 'boolean' }, output: { type: 'string' } },
}

const gate = await agent(
  `Run exactly this and nothing else, then report:

    python <the course-factory skill folder>/scripts/course_gate.py "${A.course}"

open = true only if it exited 0. output = everything it printed, word for word.
Do not fix anything, do not write any file.`,
  { label: 'gate:ilo-map+kb', phase: 'Read', schema: GATE_SCHEMA }
)

if (!gate || !gate.open) {
  /* No module agent starts without the approved ILO map and the knowledge-base decision (owner, 2026-10-16). */
  return {
    stopped_at: 'GATE',
    why: 'No module starts before the ILO map is approved and the knowledge-base decision is recorded.',
    gate: gate ? gate.output : 'the gate check did not run',
  }
}

/* ------------------------------------------------- 1..N · BUILD, WITH QA BEHIND */

/* m.id is the module's number: 1, 2 ... - its folder is modules/module01 (L45), its script M01 */
const two = (m) => String(m.id).replace(/\D/g, '').padStart(2, '0')

const build = (m) => `Invoke ${SKILL} and follow it. Build ONE module.

  Course folder:   ${A.course}
  Your module:     ${m.id} — ${m.title}
  Your minutes:    ${m.minutes} total (${m.theory} theory / ${m.practical} practical)

Your module is written against YOUR ROWS OF THE ILO MAP - read them first:
  ilo_map.py show ${A.course} --module ${m.id}       (course-factory/scripts)
- the Main ILO verbatim, every Sub-ILO you owe, the model-course items under your topic -
then your module in working_claude/architecture.json (incl. what it keeps, modernises and
adds from the old course, L41). Do not read the whole knowledge base: search it with
course-factory/kb/scripts/kb_tool.py search, which writes into the course folder only, and
list every source you use in the script's "sources". Every Sub-ILO is taught on a slide and
checked by a question ("sub_ilo" on both) - script/GUIDE.md "Before writing".

THE WORDS ARE TYPED ONCE (L29). Your module's content script is
working_claude/script/M${two(m)}.json (course-factory script/GUIDE.md).
  * Not approved yet: write it, make its review page and Word file, and STOP there -
    report "awaiting approval". The operator approves each script; nothing is built
    from words nobody approved.
  * Approved: you BUILD, and you never type the deck's or a task page's HTML.
    Read course-factory compile/GUIDE.md and the picture lanes (course-visuals: what
    each slide's picture should be, the figure kit) - NOT course-module-ux,
    course-module-ui or course-task-ux: the compiler builds their standard.
      design_system.py install modules/module${two(m)}       (course-module-ui/scripts)
      compile_module.py <course> --module ${m.id} --init-build   then fill the build sheet:
          each slide's figure (a real photo, a kit drawing, a figure file), a layout
          choice only where the script's own is not enough
      compile_module.py <course> --module ${m.id}               fix what it reports, build again
    A change goes into the script or the build sheet and is built again - never into
    the HTML. A way of answering the compiler leaves "as it is" is the one page you
    make by hand, to course-task-ux.

YOU MAY WRITE ONLY INSIDE  ${A.course}/modules/module${two(m)}/  and your own
working_claude/script/M${two(m)}.* and working_claude/figures/M${two(m)}/.
Never COURSE.html, never _course_shell/, never the start pages of another module, never
the handout, never another module. Those are assembled afterwards by one process
(compile_course.py), because two agents writing one file is a lost write that no test
catches.

The course's standards come first (L50): if ${A.course}/working_claude/STANDARDS.md exists,
read it and build to every S-line in it — they are the operator's wishes for every module
(the end slide, text size, button size ...), said once so no module needs repairing for
them again. A part every module uses lives once in ${A.course}/working_claude/shared/:
copy it into your module's assets/ (or use course-factory/scripts/fix.py sync-shared);
never write your own version of it.

Your minutes are fixed and are not negotiable — anything that will not fit becomes
self-study, and you record it so the handout can pick it up (L1).

The look is the compiler's; what the picture should be is course-visuals'. Every TOPIC
screen leads with a figure (L23) — search the source files and knowledge base first, then
the internet for a real photograph, then the figure kit, then author or generate. The
script's visual_kind "none" is how a screen honestly needs no figure. Where an image needs
generating and you cannot produce it, write the brief to _visual_briefs/ and keep going:
the module is finished as far as it can go, and the handoff is written at the end.

Report what you built (or "awaiting approval"), every honesty marker with its source, the
achieved Track A buckets and Track B ratio, what you moved to the handout, and every line
the compiler printed under "To fix" or "left as it is".`

const qa = (m) => `You did NOT build this module. Check it.

  Module:  ${A.course}/modules/module${two(m)}
  Against: its rows of the ILO map (ilo_map.py show ${A.course} --module ${m.id}) and
           its module in working_claude/architecture.json

A module whose script is not approved yet has nothing built to check: report that, with
blocking false. Otherwise run the deterministic checks and READ their output —
check_script_match, check_hours, check_balance, check_syllabus_coverage, verify_links,
audit_navigation, crosscheck_tasks, check_slide_text, check_visual_first, check_visuals,
check_assets, the drawing check compile_module.py ran (L54), and classify_module.py.

Then answer the questions no script can: is every outcome in the ILO map actually
taught here, or only mentioned? Does each figure teach something the text does not?
Would an instructor who has never seen this module be able to run it from Start and
Next alone?

A module that still classifies C has not finished — say so plainly. REPORT findings.
Do not fix anything.`

const QA_SCHEMA = {
  type: 'object',
  required: ['module', 'classification', 'blocking', 'findings'],
  properties: {
    module: { type: 'string' },
    classification: { type: 'string' },
    blocking: { type: 'boolean' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'where', 'what'],
        properties: { severity: { type: 'string' }, where: { type: 'string' }, what: { type: 'string' } },
      },
    },
  },
}

/* Module 3 is verified while Module 7 is still being written. No wasted wall-clock. */
const results = await pipeline(
  A.modules,
  (m) => agent(build(m), { label: `build:${m.id}`, phase: 'Build' }).then((r) => ({ m, r })),
  ({ m }) => agent(qa(m), { label: `qa:${m.id}`, phase: 'Verify', schema: QA_SCHEMA })
)

/* ------------------------------------------------------------ + · CROSS-CHECK */

phase('Cross-check')

const cross = await agent(
  `One pass over the WHOLE course at ${A.course} — the questions a single-module agent
could not answer:

  * task codes unique across every module, and every code the decks announce exists
  * terminology and COURSE_LANGUAGE consistent across all modules (check_language.py)
  * the hours total against the approved programme, both Track A buckets
  * one visual dialect, not several (audit_ui.py over every module's stylesheets)
  * every cross-reference between modules resolves
  * every row of working_claude/ilo_map.json is taught somewhere, and no outcome is claimed twice
  * every page reachable and every page has a way back (audit_navigation.py)
  * nothing at RIGHTS_REVIEW_REQUIRED, no honesty marker on a course-facing page

Report. Do not fix.`,
  { label: 'crosscheck:course', phase: 'Cross-check', schema: QA_SCHEMA }
)

const blocking = results.filter((q) => q && q.blocking)

return {
  modules: A.modules.length,
  qa: results,
  cross,
  blocking: blocking.map((q) => q.module),
  next: blocking.length
    ? 'Blocking findings. Fix them in the named modules before assembly.'
    : 'Approve every script still awaiting approval and run pass 2 again (approved modules are rebuilt '
      + 'from their scripts, unchanged ones stay the same bytes). Then assemble, one process, not an '
      + 'agent each: compile/scripts/compile_course.py <course> (COURSE.html, course_map.js, every '
      + 'module\'s start pages), scripts/check_course_package.py <course>/modules, the handout, the run '
      + 'content. Then course-tablet-publisher.',
}
