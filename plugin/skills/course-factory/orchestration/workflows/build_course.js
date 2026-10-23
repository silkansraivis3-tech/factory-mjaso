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
 * `factory` (optional): a folder holding the factory's skills (`<factory>/course-factory/SKILL.md` ...) to use
 *   instead of the installed plugin - a benchmark pins its version this way.
 * `notes` (optional): the operator's words for every module agent ("no paid pictures tonight", "decline 3D: ...").
 *
 * Models (2.51.0, the M01 benchmark: the mechanical loop was most of the bill): the reader and the script writer
 * keep the session's model - that is where the words come from. Building an approved script (build_module.py
 * until PASS, the review, the fixes) and QA run on Sonnet at medium effort; the gate, one command, at low.
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
const SKILL = A.factory
  ? `the course-factory skill at ${A.factory}/course-factory/SKILL.md (read it as the Skill tool would, and use the `
    + `scripts and guides under ${A.factory} - not the installed plugin)`
  : 'the course-factory skill (Skill tool, name "course-factory")'
const SCRIPTS = A.factory ? `${A.factory}/course-factory` : '<the course-factory skill folder>'
const NOTES = A.notes ? `\n\nTHE OPERATOR SAYS, FOR THIS RUN: ${A.notes}` : ''
/* the mechanical work - building an approved script, checking it - on Sonnet; see the header */
const MECHANICAL = { model: 'sonnet', effort: 'medium' }

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

if (!A.modules || !A.modules.length) {
  /* Pass 1 only: the reader writes the Stage 2 files. Pass 2 never runs it again - it would rewrite the
     architecture and the ILO map the owner has just approved (2.49.4). */
  const plan = await agent(READ, { label: 'read:programme', phase: 'Read', schema: MAP_SCHEMA })
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
  required: ['open', 'output', 'approved'],
  properties: {
    open: { type: 'boolean' }, output: { type: 'string' },
    approved: { type: 'array', items: { type: 'string' }, description: 'the module ids whose script status says "approved"' },
  },
}

const gate = await agent(
  `Run exactly these and nothing else, in ONE shell call, then report:

    python ${SCRIPTS}/scripts/course_gate.py "${A.course}"
${A.modules.map((m) => `    python ${SCRIPTS}/scripts/content_script.py status "${A.course}" --module ${m.id}`).join('\n')}

open = true only if course_gate.py exited 0. output = everything course_gate.py printed, word for word.
approved = the module ids (as written after --module) whose status line says "approved by"; a draft, a
missing script or an error is not approved. Do not fix anything, do not write any file.`,
  { label: 'gate:ilo-map+kb', phase: 'Read', schema: GATE_SCHEMA, model: 'sonnet', effort: 'low' }
)
const APPROVED = new Set(((gate && gate.approved) || []).map(String))

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

/* what every module agent is told, the script writer and the builder alike */
const brief = (m) => `  Course folder:   ${A.course}
  Your module:     ${m.id} — ${m.title}
  Your minutes:    ${m.minutes} total (${m.theory} theory / ${m.practical} practical)

Your module is written against YOUR ROWS OF THE ILO MAP - read them first:
  ilo_map.py show ${A.course} --module ${m.id}       (course-factory/scripts)
- the Main ILO verbatim, every Sub-ILO you owe, the model-course items under your topic -
then your module in working_claude/architecture.json (incl. what it keeps, modernises and
adds from the old course, L41).

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
self-study, and you record it so the handout can pick it up (L1).${NOTES}`

/* a module whose script is not approved: the words, on the session's model, then STOP */
const writeScript = (m) => `Invoke ${SKILL} and follow it. Write ONE module's content script.

${brief(m)}

Do not read the whole knowledge base: search it with course-factory/kb/scripts/kb_tool.py
search, which writes into the course folder only, and list every source you use in the
script's "sources". Every Sub-ILO is taught on a slide and checked by a question ("sub_ilo"
on both) - script/GUIDE.md "Before writing".

THE WORDS ARE TYPED ONCE (L29). Your module's content script is
working_claude/script/M${two(m)}.json (course-factory script/GUIDE.md). Write it, make its
review page and Word file, and STOP there - report "awaiting approval". The operator
approves each script; nothing is built from words nobody approved.

Report "awaiting approval", every honesty marker with its source, the planned Track A
buckets and Track B ratio, and what you moved to the handout.`

/* an approved module: the mechanical build, on Sonnet (MECHANICAL), in ONE command per round */
const build = (m) => `Invoke ${SKILL} and follow it. BUILD ONE module from its approved script.

${brief(m)}

Your script working_claude/script/M${two(m)}.json is approved: you never type the deck's or a
task page's HTML, and you never change the approved words. Read the Quickstart at the top of
course-factory compile/GUIDE.md and follow it step by step - it is the whole build - and the
picture lanes it names (course-visuals/kit/CATALOGUE.md, never kit.js). NOT course-module-ux,
course-module-ui or course-task-ux: the compiler builds their standard.

    design_system.py install modules/module${two(m)}                     (course-module-ui/scripts)
    compile_module.py <course> --module ${m.id} --init-build              (once, if the build sheet is missing)
        (2.63.3) when working_claude/course.build.json names a "seed_from" course (a hand-fixed predecessor), every
        slide and question whose words are unchanged starts from ITS drawing or photo ("_seeded" in the sheet): build
        those as they are and change only what the build reports - they are the hand-fixed ones
    fill the build sheet, edit the starter figure specs
    build_module.py <course> --module ${m.id} --no-course-pages           (compile/scripts)
        ONE command runs the figures, the compile, every check and the review sheets and prints
        only what fails. Fix what it prints in the build sheet or the figure specs and run it
        again - never a check on its own, never the HTML. --no-course-pages: one process
        writes COURSE.html afterwards.
    STOP AT MODULE CLEAN (2.63.3): PASS, or "FAIL M${two(m)} - course package" with "MODULE CLEAN" under it
        (the package is judged after assembly) - that is the end of your build. Do NOT review the sheets
        yourself and do not polish: the QA agent behind you does the ONE visual review on the sheets this
        build promoted, and a BROKEN finding comes back to the module for one fix round. (The 2.63.2
        full-course run: 46 of 128 build calls came after module clean - a builder reviewing its own sheets,
        whose fixes tripped the layout checks again.) Anything you would polish: list it in your report.
    a figure problem: fix it in the studio (studio.py <spec> --step all, seconds), then one build.

RUN build_module.py IN THE FOREGROUND and wait for its last line; give the shell call the longest
timeout it allows (600000 ms). A build that runs longer answers "STILL BUILDING" before that
limit and goes on by itself: then run the SAME command with --wait (again, until it prints the
build's answer) - never start a second build meanwhile, never edit the build sheet or a figure while
it runs. A module's first build may first wait up to 5 min for another module's first build (one
at a time on this computer) - that is expected. Never end your turn while a build runs: your report
is read as the module's result (2.58.0 - the IGF full build: a builder that ended "waiting on the
build" left Module 15 half-built). Your report's FIRST line is the PASS / FAIL line build_module.py
printed.

A way of answering the compiler leaves "as it is" is the one page you make by hand, to
course-task-ux.

L60 (2.63.2 - the 2.63.0 full build: M08 and M10-M14 ended with no 3D scene and no word about it):
when the build prints "RECOMMENDED (L60)", build the scene on the slide it names (its starter
entry and compile/GUIDE.md 2b; smoke3d.py after each edit) - or, only when the subject has no
shape, inside or layout in space to show, or a photo is wanted there, write the reason at the
TOP of the build sheet, "declined_3d": "builder: <the reason>". Never leave it unanswered; your
report says which (the scene's slide, or the reason).

The look is the compiler's; what the picture should be is course-visuals'. Every TOPIC
screen leads with a figure (L23) — search the source files and knowledge base first, then
the internet for a real photograph, then the figure kit, then author or generate. The
script's visual_kind "none" is how a screen honestly needs no figure. Where an image needs
generating and you cannot produce it, write the brief to _visual_briefs/ and keep going:
the module is finished as far as it can go, and the handoff is written at the end.

Report: the PASS / FAIL line build_module.py printed (PASS, or the problems left) and the path of
its full log, how many build_module.py runs it took, every honesty marker with its source,
the achieved Track A buckets and Track B ratio, what you moved to the handout, every line
the compiler printed under "To fix" or "left as it is", and anything you would polish.`

const qa = (m) => `You did NOT build this module. Check it.

  Module:  ${A.course}/modules/module${two(m)}
  Against: its rows of the ILO map (ilo_map.py show ${A.course} --module ${m.id}) and
           its module in working_claude/architecture.json
  Factory: the skills folder ${A.factory || '(the installed plugin\'s skills/)'} - the checks below live in its
           course-factory/, course-visuals/ and course-module-ux/ folders

Run the deterministic checks in TWO shell calls and READ their output:
  1  python course-factory/compile/scripts/build_module.py "${A.course}" --module ${m.id} --no-course-pages --no-fix
     - the compile, the drawing check (L54), both script matches, navigation, the audits at
     1280x800 and 1024x768, the importer and the review sheets' grading of every question (right
     and wrong), in one command. It rebuilds from the same approved inputs, so the bytes come out
     the same: anything it reports, or a stop (exit 2), is a finding. Give the shell call 600000 ms;
     if it answers "STILL BUILDING", run the same command with --wait until it prints its answer.
  2  the checks it does not run - ONLY these, because only these can judge ONE module (2.63.2) - chained
     in ONE call, each by the usage line at the top of its file, printing only what fails:
       check_balance on presentation/index.html WITH THIS MODULE'S OWN allocation:
         --theory-min ${m.theory} --practice-min ${m.practical}
       (never --programme alone: that is the whole course's total row and fails every module; compiled
       decks carry data-active from 2.52.0; "100% of a theory block active" on an active slide over 10
       minutes is the owner's open decision, MANIFEST "Waiting on the owner" 2, not a finding),
       check_slide_text, check_visual_first, check_visuals, check_assets and classify_module.py.
     NOT run here, they judge the whole course and belong to the cross-check after assembly: check_hours,
     check_syllabus_coverage, crosscheck_tasks (all need COURSE_START.json / the tablet manifest / every deck),
     verify_links and audit_navigation (a link to ../START_HERE_EXTENDED.html or a page "reached from
     nothing" is what a module looks like before compile_course.py writes the course's pages).
The module's START_HERE pages, COURSE.html and course_map.js are written by compile_course.py once every
module is in: their absence, and a link to them, is not a finding of this module.

Then answer the questions no script can: is every outcome in the ILO map actually
taught here, or only mentioned? Does each figure teach something the text does not?
Would an instructor who has never seen this module be able to run it from Start and
Next alone?
And (2.63.2): does each picture show what the question or slide NAMES? Read a question or slide, then open its picture
(figure spec, photo and its _photo_meta.json "shows"): an oxygen monitor on a %LEL question, a portable explosimeter
where a fixed detector head is meant, a spectacle blind where a spool piece is asked - the IGF course passed every
check with these and they were found only by eye. A picture of a different instrument, part or place than the words
name is a finding of severity BROKEN (compile/REVIEW_PROMPT.md, item 6, is the same rule for the sheets).

THE ONE VISUAL REVIEW (2.63.3 - the builder stops at module clean and no longer reviews its own sheets): the
review sheets of this module are in ${A.course}/working_claude/review/M${two(m)}/ (sheet_01.png ...; sheets.json
names the screens on each) - the screens changed since the last review, promoted by the build above. Look at
each sheet ONCE, in order, against course-factory/compile/REVIEW_PROMPT.md, and note findings as you go (never
re-open a sheet you have read). Then mark them looked at, so the next sheets show only what changes after this:
  python course-factory/compile/scripts/build_module.py "${A.course}" --module ${m.id} --reviewed
Write the POLISH findings, one line each, to working_claude/review/M${two(m)}_POLISH.md (beside the folder, never
inside it - a promotion replaces the folder).

A module that still classifies C has not finished — say so plainly. REPORT findings.
Do not fix anything. Severity is one of three (2.63.3 - the 2.63.2 run's QA used five scales):
  BROKEN  wrong, misleading or unusable for a trainee or the instructor - a picture of another thing than the
          words name, a number that contradicts the slide, a question graded wrongly, an outcome not taught, a
          failed check; blocking = true when there is one
  POLISH  works, could look or read better
  INFO    worth knowing, nothing to change`

/* 2.63.3 - a BROKEN finding of QA sends the module back for ONE fix round, by a builder who fixes exactly those */
const fixRound = (m, q) => `${build(m)}

THIS MODULE IS BUILT AND WAS CHECKED BY QA. Do NOT start again from --init-build. Fix EXACTLY these BROKEN
findings - nothing else (no polish, no other screen) - in the build sheet or the figure specs, then run
build_module.py until module clean (PASS, or only the course package left) and STOP. A finding that needs the
approved words changed is not yours to fix: say so in your report. The findings:

${((q && q.findings) || []).filter((f) => f.severity === 'BROKEN').map((f) => `  - ${f.where}: ${f.what}`).join('\n')}`

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
        properties: {
          severity: { type: 'string', enum: ['BROKEN', 'POLISH', 'INFO'] },
          where: { type: 'string' }, what: { type: 'string' },
        },
      },
    },
  },
}
const broken = (q) => ((q && q.findings) || []).some((f) => f.severity === 'BROKEN')

/* Module 3 is verified while Module 7 is still being written. No wasted wall-clock.
   An approved module is built and checked on Sonnet; a draft gets its script written on the session's model and
   has nothing built to check, so no QA agent is spent on it. */
/* 2.58.0 - a builder's report is checked, not trusted: no "PASS" line from build_module.py (only the course package
   failing counts as passed in a parallel build - it is judged after assembly) and a fresh agent carries the module on
   from its files, at most A.retries times (default 1). The IGF full build's Module 15 builder ended mid-build */
const passed = (r) => /\bPASS (M\d+|final)\b/.test(String(r || '')) ||
  /\bFAIL (M\d+|final) - course package \(/.test(String(r || ''))
const carryOn = (m, last) => `${build(m)}

THIS MODULE WAS STARTED BY ANOTHER AGENT, WHICH STOPPED BEFORE build_module.py printed PASS. Its
build sheet, figure specs and pages are where it left them - do NOT start again from --init-build.
Run build_module.py (with --wait first if a build of it is still running), fix what it prints, until module
clean, then STOP - QA does the review. Its last report was:

${String(last || '(no report)').slice(0, 2500)}`
async function buildUntilPass(m) {
  let r = await agent(build(m), { label: `build:${m.id}`, phase: 'Build', ...MECHANICAL })
  for (let k = 1; k <= (A.retries === undefined ? 1 : A.retries) && !passed(r); k++) {
    log(`module ${m.id}: no PASS in the builder's report - a fresh agent carries it on (${k})`)
    r = await agent(carryOn(m, r), { label: `build:${m.id}+${k}`, phase: 'Build', ...MECHANICAL })
  }
  return r
}

/* the modules in waves of A.wave (default: all at once) - each build runs headless browsers, so on one PC a wave of 3
   keeps it from being pinned at 99 % (the IGF full build ran in waves of 3) */
const WAVE = A.wave || A.modules.length
const results = []
for (let i = 0; i < A.modules.length; i += WAVE) {
  const chunk = A.modules.slice(i, i + WAVE)
  if (WAVE < A.modules.length) log(`wave ${i / WAVE + 1}: modules ${chunk.map((m) => m.id).join(', ')}`)
  results.push(...await pipeline(
    chunk,
    (m) => APPROVED.has(String(m.id))
      ? buildUntilPass(m).then((r) => ({ m, r, built: true }))
      : agent(writeScript(m), { label: `script:${m.id}`, phase: 'Build' }).then((r) => ({ m, r, built: false })),
    ({ m, built }) => built
      ? agent(qa(m), { label: `qa:${m.id}`, phase: 'Verify', schema: QA_SCHEMA, ...MECHANICAL }).then((q) => ({ m, q }))
      : { m, q: { module: String(m.id), classification: 'AWAITING APPROVAL - script written, nothing built', blocking: false, findings: [] } },
    /* 2.63.3 - BROKEN: one fix round, then QA once more (its sheets show only the screens the fix changed); never a third */
    async ({ m, q }) => {
      if (!broken(q)) return q
      log(`module ${m.id}: QA found BROKEN - one fix round`)
      await agent(fixRound(m, q), { label: `fix:${m.id}`, phase: 'Build', ...MECHANICAL })
      const q2 = await agent(qa(m), { label: `qa:${m.id}+fix`, phase: 'Verify', schema: QA_SCHEMA, ...MECHANICAL })
      return q2 ? Object.assign({}, q2, { first_qa: q.findings }) : q
    }
  ))
}

/* the final assessment (args.final), when its script is approved - built after the modules it draws on */
const finalReport = A.final ? await agent(`Invoke ${SKILL} and follow it. BUILD the FINAL ASSESSMENT from its approved script.

  Course folder:   ${A.course}
  The final:       working_claude/script/FINAL.json (approved), built into the module folder after the last
                   planned module (variants A and B are both graded: final_a.html / final_b.html - compile/GUIDE.md)

    compile_module.py <course> --module final --init-build      (once, if the build sheet is missing)
    fill the build sheet; build_module.py <course> --module final --no-course-pages   until PASS - in the
    FOREGROUND, never ending your turn while it runs
    then the review the Quickstart names (BROKEN fixed, POLISH listed in working_claude/review/FINAL/POLISH.md)

You may write only inside the final's module folder and working_claude/script/FINAL.* and working_claude/figures/FINAL/.
Report: FIRST line = the last line build_module.py printed; then how many runs it took and what the review found.${NOTES}`,
  { label: 'build:final', phase: 'Build', ...MECHANICAL }) : null

/* ------------------------------------------------- + · ASSEMBLY (2.58.0), then CROSS-CHECK */

phase('Cross-check')
/* one process writes the course's own pages once every module is in (Rule 3), the ILO map is refreshed from the scripts,
   and only then is the whole course judged - before, the cross-check ran on a course with no START_HERE pages and
   called every module unreachable, and the ILO map still said "planned - module not built" */
const assembly = await agent(`Run exactly these, in ONE shell call, and report what they printed (the last 40 lines each):

    python ${SCRIPTS}/compile/scripts/compile_course.py "${A.course}"
    python ${SCRIPTS}/scripts/ilo_map.py refresh "${A.course}"
    python ${SCRIPTS}/scripts/check_course_package.py "${A.course}/modules"
    python ${SCRIPTS}/retrofit/scripts/check_terms.py "${A.course}"
    python ${SCRIPTS}/retrofit/scripts/check_numbers.py "${A.course}"

check_terms.py (2.63.2) is the course-wide terminology report - one thing under two names (LEL / LFL, bunkering
station / bunker station ...) from the factory's list plus working_claude/terms.json. check_numbers.py (2.63.2) is the
same for numbers - one quantity under two values (H2S 20 ppm on a slide, 25 ppm in a question; oxygen 20.9 % and
21 %). Both are REPORTS, never a failure: print all of each, word for word, for the cross-check and the operator.
Do not fix anything.`,
  { label: 'assemble:course', phase: 'Cross-check', model: 'sonnet', effort: 'low' })

const cross = await agent(
  `One pass over the WHOLE course at ${A.course} — the questions a single-module agent
could not answer:

  * task codes unique across every module, and every code the decks announce exists
  * COURSE_LANGUAGE consistent across all modules (check_language.py)
  * terminology: one thing, one name - the check_terms.py report the assembly printed (a MIXED group is a finding of
    severity "warn" naming the forms, the modules and slides; the operator picks the form, never you); read the
    scripts for any other pair the list does not hold (a room, an extinguishing agent)
  * numbers: one quantity, one value - the check_numbers.py report the assembly printed (a DIFFERS quantity is a finding
    of severity "warn" naming the values and the slides / questions; a different value can be right - another gas, another
    standard - so the operator picks the one the course keeps, never you)
  * the hours total against the approved programme, both Track A buckets (check_hours.py, with the programme)
  * the syllabus coverage against the model course (check_syllabus_coverage.py), crosscheck_tasks.py and verify_links.py -
    the checks that need every module, which the single-module QA agents were told to leave to this pass
  * one visual dialect, not several (audit_ui.py over every module's stylesheets)
  * every cross-reference between modules resolves
  * every row of working_claude/ilo_map.json is taught somewhere, and no outcome is claimed twice
  * every page reachable and every page has a way back (audit_navigation.py)
  * nothing at RIGHTS_REVIEW_REQUIRED, no honesty marker on a course-facing page

Report. Do not fix.`,
  { label: 'crosscheck:course', phase: 'Cross-check', schema: QA_SCHEMA }
)

/* a module whose build or QA brought back nothing is not verified - it blocks, it is never counted as clean */
const blocking = results
  .map((q, i) => q || { module: String(A.modules[i].id), blocking: true, classification: 'NOT VERIFIED - no QA result' })
  .filter((q) => q.blocking)

return {
  modules: A.modules.length,
  qa: results,
  final: finalReport,
  assembly,
  cross,
  blocking: blocking.map((q) => q.module),
  next: blocking.length
    ? 'Blocking findings. Fix them in the named modules, then run compile_course.py and check_course_package.py again.'
    : 'Approve every script still awaiting approval and run pass 2 again (approved modules are rebuilt '
      + 'from their scripts, unchanged ones stay the same bytes). The course pages are assembled above; then '
      + 'the handout, the run content, and course-tablet-publisher.',
}
