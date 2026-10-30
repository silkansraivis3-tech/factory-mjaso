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
 * `seed_from` (optional, 2.71.0): the hand-fixed predecessor course a rebuild starts from - every module's --init-build
 *   takes its drawings and photos for the screens whose words are unchanged (compile_module.py --seed-from). Without it
 *   the course's own working_claude/course.build.json "seed_from" is used, when it names one.
 * `wave` (optional): how many modules build at once (default: all). 2.71.0 - a rolling pool, biggest module first: the
 *   gate measures each module's build cost (scripts/build_order.py) and the next module starts as soon as one finishes,
 *   so the long pole starts first instead of a wave waiting for its slowest member (2.63.3 M01-M03: 114 min, M02 alone).
 *
 * 2.71.0 - the builder reads compile/BUILDER_CARD.md, not the whole skill; a module with a 3D-kit scene gets the 3D step
 * after its build: scene3d_check.py (spec, smoke, timing, pictures), a SEPARATE reviewer of the pictures, one fix round.
 *
 * 2.72.0 - then the FIGURE step: every kit figure photographed at projector size at every step (figure_review.py), judged
 * by a reviewer who did not build it against the slide's words and the figure's must-be-true list; BROKEN goes back once.
 *
 * 2.72.5 - the 3D step, the FIGURE step and QA judge the built module AT THE SAME TIME, and ONE fix round (two builds, at
 * most six studio runs a figure) takes every BROKEN finding of the three; then only what was BROKEN is judged again
 * (Desktop\IGF_course_2.66_figures\SPEED_ANALYSIS.md: up to three fixers one after the other on one module before).
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
const CARD = A.factory ? `${SCRIPTS}/compile/BUILDER_CARD.md`
  : 'compile/BUILDER_CARD.md in the course-factory skill\'s folder (the Skill tool, name "course-factory", names the folder)'
const SEED = A.seed_from ? ` --seed-from "${A.seed_from}"` : ''
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
    order: {
      type: 'array', description: 'build_order.py --json, as printed: the modules biggest first',
      items: { type: 'object', required: ['id', 'cost'], properties: { id: { type: 'number' }, cost: { type: 'number' } } },
    },
    skill_dir: { type: 'string', description: 'the absolute folder of the course-factory skill the scripts ran from (it holds SKILL.md and scripts/)' },
  },
}

const gate = await agent(
  `Run exactly these and nothing else, in ONE shell call, then report:

    python ${SCRIPTS}/scripts/course_gate.py "${A.course}"
${A.modules.map((m) => `    python ${SCRIPTS}/scripts/content_script.py status "${A.course}" --module ${m.id}`).join('\n')}
    python ${SCRIPTS}/scripts/build_order.py "${A.course}" --modules ${A.modules.map((m) => m.id).join(',')} --json${SEED}

open = true only if course_gate.py exited 0. output = everything course_gate.py printed, word for word.
approved = the module ids (as written after --module) whose status line says "approved by"; a draft, a
missing script or an error is not approved. order = the JSON list build_order.py printed, as it is (empty if it
printed none). skill_dir = the absolute folder of the course-factory skill these
scripts ran from${A.factory ? '' : ' (find it with Glob - **/skills/course-factory/SKILL.md under the installed plugins, the newest version - and do not read that file)'}.
Do not fix anything, do not write any file.`,
  { label: 'gate:ilo-map+kb', phase: 'Read', schema: GATE_SCHEMA, model: 'sonnet', effort: 'low' }
)
const APPROVED = new Set(((gate && gate.approved) || []).map(String))
/* 2.71.0 - biggest module first (build_order.py's cost); a module it did not cost keeps its place after the costed ones.
   (merge) Approved modules first, and with no cost from the gate the most minutes in the approved table (Raivis's 2.65.0) */
const COST = new Map(((gate && gate.order) || []).map((r) => [String(r.id), Number(r.cost) || 0]))
const size = (m) => (COST.size ? COST.get(String(m.id)) || 0 : Number(m.minutes) || 0)
const ORDER = A.modules.map((m, i) => ({ m, i }))
  .sort((a, b) => (APPROVED.has(String(b.m.id)) - APPROVED.has(String(a.m.id))) || size(b.m) - size(a.m) || a.i - b.i)
const LONG_POLE = ORDER.length > 1 && COST.size ? String(ORDER[0].m.id) : null
/* 2.66.0 (Raivis) - the factory's folder, for the builders: they read their instructions by path instead of loading the whole
   skill (SKILL.md, 48 KB - the router for every mode), and that ~12,000 tokens stays out of every builder's context for its
   whole run (the timed gas M02 build: 84 tool calls). (merge) What they read by it is the builder card */
const DIR = A.factory ? `${A.factory}/course-factory` : ((gate && gate.skill_dir) || '').replace(/[\\/]SKILL\.md$/i, '') || null
const CARD_AT = DIR ? `${DIR}/compile/BUILDER_CARD.md` : CARD

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

/* 2.73.0 - the course's ONE photo-sourcing pass (chem advanced, 2026-10-27: one photo agent per script, each searching the
   same old-course and knowledge-base pictures). The catalogue (scripts/photo_catalogue.py) already holds every picture the
   course owns; this pass finds only what PHOTOS_TO_FIND.md lists, and saves it where the builds take it with no agent */
const photoPass = (when) => `You are the course's ONE photo-sourcing pass (2.73.0) - ${when}. Course: ${A.course}

  python ${SCRIPTS}/scripts/photo_catalogue.py index "${A.course}"     (only if working_claude/photo_catalogue.json is missing)
  python ${SCRIPTS}/scripts/photo_catalogue.py assign "${A.course}"

Then work down working_claude/visuals/PHOTOS_TO_FIND.md: for each row MAKE ONE PHOTOREALISTIC GENERATED picture of what it
must show (2.73.2, owner 2026-10-28: nobody is asked to take a photo; equipment is generated too - it is fixed afterwards):
nano-banana's generate_image (or another image tool the session has), a prompt from the row's "must show" and its slot's
shape, true to how the thing looks on a chemical / gas tanker, no words or numbers in the picture, 1600 px or more on its
long side - within the course's approved picture budget (intake.json "picture_budget"; none recorded: stop and report).
Open and look at each before you keep it. Save it into ${A.course}/working_claude/photos_found/<module, e.g. M04>/ with its
record in that folder's _photo_meta.json: title, "generated": true, source (the tool), the prompt, description of what it
LITERALLY shows, shows, visually_verified, and "found_for": "<the row's slot, e.g. M04 s05>".
Then run photo_catalogue.py assign again: a photo found for a slot becomes that slot's pick, and the builds take it with no
agent. You may write only into working_claude/photos_found/ - never a module, a script or a build sheet.
Report how many rows you found, and the rows you could not.${NOTES}`

/* 2.73.0 - PHASE A, with no agent (chem advanced: 18 builder agents at once hit the 20-subagent cap, the CPU sat at 100 %
   and the browser slots serialised them - the agents mostly waited, every wait a model turn). phase_a.py builds every
   approved module as far as it goes in ONE local queue sized by the computer's browser slots: --init-build (his prefill,
   then placeholders of each picture slot's shape), the whole build, --auto picks. A module it brings to PASS or MODULE
   CLEAN gets no builder; the rest get one whose brief is the module's needs file. Bench chem M11/M17/M18: 84 s, no agent */
const PHASE_A_SCHEMA = {
  type: 'object', required: ['modules'],
  properties: { modules: { type: 'array', items: { type: 'object', required: ['module', 'line'],
    properties: { module: { type: 'string', description: 'the module number, as in --modules' },
                  line: { type: 'string', description: "phase_a.py's line for it, word for word" } } } } },
}
const phaseAPrompt = (ids) => `Run, in the FOREGROUND with the longest timeout the shell allows (600000 ms):

    python ${SCRIPTS}/scripts/photo_catalogue.py index "${A.course}"      (only if working_claude/photo_catalogue.json is missing)
    python ${SCRIPTS}/scripts/photo_catalogue.py assign "${A.course}"
    python ${SCRIPTS}/compile/scripts/phase_a.py "${A.course}" --modules ${ids.join(',')}

phase_a.py builds every module as far as it goes with no agent and prints one line per module. If it answers STILL
RUNNING, run  python ${SCRIPTS}/compile/scripts/phase_a.py "${A.course}" --wait  again, until it prints its lines. Never
start a second run, never edit a file. Report each module's line word for word (modules: [{module, line}]).`

/* an approved module: the mechanical build, on Sonnet (MECHANICAL), in ONE command per round */
/* 2.71.0 - the builder reads a one-page card (compile/BUILDER_CARD.md: the commands, the fix for each kind of line the
   build prints, the stop, the report), not the whole skill: the 2.63.3 builders read ~130,000 characters of SKILL.md,
   GUIDE.md, CATALOGUE.md and SPEC.md first and carried them in every turn (M02: 98 M cache-read tokens) */
const build = (m) => `BUILD ONE module from its approved script. Read ${CARD_AT} first - it is your whole job: the commands,
what to do with each line the build prints, when to stop and what to report. Do NOT read the course-factory SKILL.md
or load the skill (2.66.0: ~12,000 tokens in your context for your whole run); compile/GUIDE.md${DIR ? ` (${DIR}/compile/GUIDE.md)` : ''}
is reference for a case the card does not cover - read only the section it names. The factory's scripts are under
${DIR ? `${DIR}/..` : `${SCRIPTS}/..`} (course-factory, course-visuals, course-module-ui, course-module-ux) - use those, not another copy.

${brief(m)}

Your script working_claude/script/M${two(m)}.json is approved: you never type the deck's or a task page's HTML, and you
never change the approved words. Its photographs' candidates are in the course photo catalogue (2.73.0):
working_claude/visuals/M${two(m)}_VISUAL_NEEDS.md lists each picture slot's, and the course's one sourcing pass saves what it
finds in working_claude/photos_found/ - use those first.

    design_system.py install modules/module${two(m)}                     (course-module-ui/scripts)
    compile_module.py <course> --module ${m.id} --init-build${SEED}      (once, if the build sheet is missing)
        screens marked "_seeded" start from a hand-fixed predecessor's drawing or photo: build them as they are and
        change only what the build reports
    fill the blanks the build names in the build sheet, then BUILD - the starter figures are drawn already: never delete
        or rewrite one, never polish a figure the build did not name (2.72.0: the first proof run's builders redrew every
        figure by hand before building - 50 minutes, nothing built)
    build_module.py <course> --module ${m.id} --no-course-pages${String(m.id) === LONG_POLE ? ' --long-pole' : ''}           (compile/scripts)
        ONE command runs the figures, the compile, every check and the review sheets and prints only what fails, one
        line each with its fix. Fix it in the build sheet or the figure specs and run it again - never a check on its
        own, never the HTML.${String(m.id) === LONG_POLE ? `
        --long-pole: this module is the course's biggest build (build_order.py) - its first build goes first.` : ''}
    STOP AT MODULE CLEAN: PASS, or "FAIL M${two(m)} - course package" with "MODULE CLEAN" under it.
        Do NOT review the sheets yourself and do not polish: the QA agent behind you does the ONE visual review, and a
        BROKEN finding comes back for one fix round. Anything you would polish: list it in your report.
    THE SAME FINDING THREE BUILDS RUNNING: the build says so ("SAME FINDING 3 BUILDS RUNNING") - never build for it again,
        list it in your report; when it says "STOP - everything ... 3 builds running", STOP and report: the judges and
        the one fix round take it from there (2.72.5: M02 s05 failed in all 20 of its builds).
    a figure problem the build PRINTED: fix that figure in the studio (studio.py <spec> --quick, seconds; one --step all
        to look when it is clean), then one build.
    a layout you change (2.72.7): build_module.py <course> --module ${m.id} --slides <the slide ids> first - seconds, nothing
        written; the build's own pre-check already tries a wider words' column, paged words and the other ways by itself.

RUN build_module.py IN THE FOREGROUND and wait for its last line; give the shell call the longest
timeout it allows (600000 ms). A build that runs longer answers "STILL BUILDING" before that
limit and goes on by itself: then run the SAME command with --wait (again, until it prints the
build's answer) - never start a second build meanwhile, never edit the build sheet or a figure while
it runs. A module's first build may first wait up to 5 min for another module's first build (one
at a time on this computer) - that is expected. Never end your turn while a build runs: your report
is read as the module's result (2.58.0 - the IGF full build: a builder that ended "waiting on the
build" left Module 15 half-built). Your report's FIRST line is the PASS / FAIL line build_module.py
printed; its SECOND line the "TIME M0N: ..." line it printed under the PASS, as it is (2.65.0 - the gold
standard is 30-40 minutes a module, 20 for its fixes).

L60: when the build prints "RECOMMENDED (L60)", build the scene on the slide it names (a 3D-kit spec, sNN.kit3d.json) - or,
only when the subject has no shape, inside or layout in space to show, or a photo is wanted there, write the reason at the
TOP of the build sheet, "declined_3d": "builder: <the reason>". Never leave it unanswered. A 3D-kit scene is checked and
photographed by the workflow's 3D step after you, and judged by a reviewer who did not build it.

Every TOPIC screen leads with a picture (L23): the source files and the knowledge base first, then a real photograph, then
the figure kit. visual_kind "none" is how a screen honestly needs none. An image you cannot produce: its brief in
_visual_briefs/, and keep going.

Report as the card says.`

const qa = (m) => `You did NOT build this module. Check it.

  Module:  ${A.course}/modules/module${two(m)}
  Against: its rows of the ILO map (ilo_map.py show ${A.course} --module ${m.id}) and
           its module in working_claude/architecture.json
  Factory: the skills folder ${A.factory || '(the installed plugin\'s skills/)'} - the checks below live in its
           course-factory/, course-visuals/ and course-module-ux/ folders

Run the deterministic checks in TWO shell calls and READ their output:
  1  python course-factory/compile/scripts/build_module.py "${A.course}" --module ${m.id} --no-course-pages --no-fix
     - the compile, the drawing check (L54), both script matches, navigation, the audits at
     1280x800, 1024x768 and 1280x720, the importer and the review sheets' grading of every question (right
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

YOURS: the words, the ILO teaching, the task pages, the photographs and the build. NOT YOURS - the kit figures
(working_claude/figures/M${two(m)}/*.kit.json, a drawing on a dark panel): the FIGURE review judges every one at
projector size, step by step, at the same time as you - how it is drawn, its labels, its parts, whether each step shows
its title (2.72.7: in the 2.72.5 run ~13-16 of QA's 24 first BROKEN were the figure review's ground, and the fixer read
each fault twice). A kit figure's drawing is never a finding of yours; a drawing that is not a kit figure still is.

Then answer the questions no script can: is every outcome in the ILO map actually
taught here, or only mentioned? Does each slide's picture earn its place - teach something the text does not?
Would an instructor who has never seen this module be able to run it from Start and
Next alone?
And (2.63.2): does each PHOTOGRAPH show what the question or slide NAMES? Read a question or slide, then open its photo
and its _photo_meta.json "shows": an oxygen monitor on a %LEL question, a portable explosimeter
where a fixed detector head is meant, a spectacle blind where a spool piece is asked - the IGF course passed every
check with these and they were found only by eye. A picture of a different instrument, part or place than the words
name is a finding of severity BROKEN (compile/REVIEW_PROMPT.md, item 6, is the same rule for the sheets).

THE ONE VISUAL REVIEW (2.63.3 - the builder stops at module clean and no longer reviews its own sheets): the
review sheets of this module are in ${A.course}/working_claude/review/M${two(m)}/ (sheet_01.png ...; sheets.json
names the screens on each) - the screens changed since the last review, promoted by the build above. Look at
each sheet ONCE, in order, against course-factory/compile/REVIEW_PROMPT.md, and note findings as you go (never
re-open a sheet you have read). A kit figure on a sheet: only the slide around it (its words, its layout) is yours. Then mark them looked at, so the next sheets show only what changes after this:
  python course-factory/compile/scripts/build_module.py "${A.course}" --module ${m.id} --reviewed
Write the POLISH findings, one line each, to working_claude/review/M${two(m)}_POLISH.md (beside the folder, never
inside it - a promotion replaces the folder).

A module that still classifies C has not finished — say so plainly. REPORT findings.
Do not fix anything. Severity is one of three (2.63.3 - the 2.63.2 run's QA used five scales):
  BROKEN  wrong, misleading or unusable for a trainee or the instructor - a picture of another thing than the
          words name, a number that contradicts the slide, a question graded wrongly, an outcome not taught, a
          failed check (a FIGURE line of the build too: say it once, as the build prints it); and (2.72.0) ANY
          drawing that is not a kit figure a seafarer would call wrong: a wrong physical arrangement (a vent
          mast or manifold inside the hull), a part the slide or a label names that is not drawn, something
          unconnected or floating, an incomplete figure - never POLISH (REVIEW_PROMPT.md item 7); blocking = true
          when there is one
  POLISH  works, could look or read better
  INFO    worth knowing, nothing to change
A BROKEN finding whose fix is in the APPROVED SCRIPT (its words, a screen's kind or minutes - e.g. check_balance counting
a "Your turn" activity's minutes as practice in a theory-only module) is the operator's: start its "where" with
"SCRIPT:" - it is reported, never sent back to a builder (who may not change an approved script).`

/* 2.63.3 - a BROKEN finding of QA sends the module back for ONE fix round, by a builder who fixes exactly those */
/* 2.72.0 - the second proof run: the three figure fixers ran 58-102 minutes and $50 between them (one 102 min, $33),
   rebuilding after every word they moved to fit a 480 px column - "build until module clean" had no end. A fix round
   gets TWO builds; what the second still prints is the operator's list (NOTHING LOOPS, approved by Aleksis) */
const FIX_CAP = `AT MOST TWO build_module.py runs in this round. Try every figure you change in the studio first -
python ${A.factory ? `${A.factory}/course-visuals/kit/scripts` : '<the course-visuals skill folder>/kit/scripts'}/studio.py <spec> --quick
(its findings in seconds, no pictures; a closer fit the build applied is already in the spec) until its own report is
clean, then ONE look at it with --step all, THEN one build. A slide whose layout or words' room you change (a "split",
"parts", a template, a picture): check it first with build_module.py "${A.course}" --module <N> --slides <its id> (2.72.7:
the deck laid out in memory, the slide audited at both sizes and its neighbours compared, in seconds - nothing written). AT MOST SIX studio runs for any one figure (2.72.5 - the
second proof run's M03 fixer ran its studio script 59 times, 58 min, on one drawing): a figure still not clean after
its sixth is left as it is and listed in your report. After the second build STOP, whatever it prints: list what it
still prints in your report (it goes to the operator's list) - never a third build, never another round of fitting words.`
/* 2.72.5 - ONE fix round per module for everything its judges found (SPEED_ANALYSIS.md, Desktop\IGF_course_2.66_figures):
   the 3D review, the FIGURE review and QA judge the built module at the same time (oneModule) and ONE fixer gets every
   BROKEN finding - before, up to three fixers ran one after the other on the same module (3D, figures, QA), each
   re-reading the card, the specs and the sheets, each with its own builds (the 2.72.3 run: 13 min of reviews before
   M01's first fixer; run 2: figure fixers 58-102 min) */
const fixAll = (m, b3, bf, bq, figs) => `${build(m)}

THIS MODULE IS BUILT AND WAS JUDGED by reviewers who did not build it${[b3.length && ' (3D)', bf.length && ' (FIGURES)',
  bq.length && ' (QA)'].filter(Boolean).join('')}. Do NOT start again from --init-build. Fix EXACTLY the BROKEN findings
below - nothing else (no polish, no other screen) - in the build sheet, the figure specs or the 3D scene specs, then
${figs ? `STOP.
DO NOT RUN build_module.py (2.72.7): figure fixers are changing the figures of ${figs.join(', ')} beside you - never edit those
figures' specs - and ONE build runs after all of you. Check a layout you change with build_module.py "${A.course}" --module
${m.id} --slides <its id> (seconds, nothing written); a 3D scene with its own check script, not a build.` : `build and STOP.
${FIX_CAP}`}
NEVER edit working_claude/script/M${two(m)}.json - not a word, not a "kind", not a minute: ANY change to the approved
script un-approves it and the module no longer builds (2.63.3 measurement: a fix round changed s05's "kind" to move
5 minutes, and M02 stopped compiling). Never run content_script.py approve / apply. A finding whose fix is in the script
is the operator's: leave it, and say so in your report.${bf.length ? `

FIGURE findings (judged at projector size; the figure specs are in working_claude/figures/M${two(m)}/).
${FIG_HOW}

${bf.map((f) => `  - ${f.slide}: ${f.what}`).join('\n')}` : ''}${b3.length ? `

3D findings (fix them in the scene's spec, sNN.kit3d.json, or the module's assets/kit3d_parts.js - course-visuals/kit3d/
SPEC.md, PARTS.md; after your build run python ${KIT3D_SCRIPTS}/scene3d_check.py "${A.course}" --module ${m.id} once):

${b3.map((f) => `  - ${f.where}: ${f.what}`).join('\n')}` : ''}${bq.length ? `

QA findings:

${bq.map((f) => `  - ${f.where}: ${f.what}`).join('\n')}` : ''}`

/* 2.72.7 - THE FIX ROUND SPLIT BY FIGURE (Desktop\IGF_course_2.66_figures\NEXT_ROUND.md #5): the 2.72.5 run's ONE fixer per
   module carried every BROKEN finding of three reviews - M03's ran 37 min (28 figure findings, 48 studio runs one after the
   other, 12.7 min of thinking), M02's 29. Now each figure with BROKEN findings gets its own small fixer, at most FIG_FIXERS
   at once (the computer's hidden-browser slots), each with its own studio cap and writing only its own spec; the 3D and QA
   findings go to one module fixer beside them that does not build; then ONE build, then the re-checks as before */
const FIG_FIXERS = 3
const KIT_SPEC = A.factory ? `${A.factory}/course-visuals/kit/SPEC.md` : '<the course-visuals skill folder>/kit/SPEC.md'
const FIG_HOW = `Where a pattern fits the figure, start from it (course-visuals/kit/patterns/, SPEC.md "Patterns": ship_ga,
bunkering_line, vent_system, fuel_supply, engine_modes, fuel_types, fuel_space_access) and place every part by what it stands
on or joins - "on", "in", "at", "from"/"to" (SPEC.md "Relations") - never by guessed raw coordinates. A finding you are sure is
RIGHT on purpose (the pipe runs on to the shore, the words name what the slide says): leave the drawing and say why in the
spec's "meaning_ok": {"<KIND> <part id>": "<why it is right>"} - the next reviewer reads it.`
const fixFig = (m, slide, fs) => `FIX ONE FIGURE of module ${m.id} - slide ${slide} - for exactly the BROKEN findings below, judged
at projector size (1920 x 1080) by a reviewer who did not build it. Nothing else: no polish, no other figure.

  Course folder:  ${A.course}
  The figure:     the kit spec the build sheet working_claude/script/M${two(m)}.build.json names as slide ${slide}'s "figure"
                  (in working_claude/figures/M${two(m)}/); the slide's words: working_claude/script/M${two(m)}.json (read only)
  The kit:        ${KIT_SPEC} - read only the sections "Relations" and "Patterns", and a part's line in CATALOGUE.md beside it

YOU MAY WRITE ONLY THAT ONE SPEC FILE - never the build sheet, another figure, the approved script or a module file. NEVER run
build_module.py: other fixers work on this module beside you, and ONE build runs after all of you (not yours).

Work in the studio: python ${KIT_SCRIPTS}/studio.py <the spec> --quick (its findings at both sizes in seconds, every step,
its real slide, no pictures) until its report is clean, and python ${KIT_SCRIPTS}/kit_meaning.py <the spec> (what the figure
means - every BLOCK fixed); then ONE look with --step all. AT MOST SIX studio runs: a figure still not clean after its sixth
is left as it is and listed in your report.
${FIG_HOW}

FIGURE findings for ${slide}:

${fs.map((f) => `  - ${f.what}`).join('\n')}

Report: the spec's path, what you changed, how many studio runs, and what is still not clean.${NOTES}`
/* the build after the split round: ONE build of what the fixers changed, at most two runs, then STOP */
const fixBuild = (m, b3, figs) => `${build(m)}

THIS MODULE WAS JUST FIXED by ${figs.length} figure fixer(s) (${figs.join(', ')})${b3.length ? ' and a module fixer (3D, QA)' : ''},
none of whom built it. Do NOT start again from --init-build and change nothing the build does not print. Run build_module.py
ONCE; if it prints a problem the fixers' changes made, fix exactly that and run it once more - AT MOST TWO build_module.py
runs, then STOP whatever it prints and list what it still prints in your report (it goes to the operator's list).${b3.length ? `
After your last build run python ${KIT3D_SCRIPTS}/scene3d_check.py "${A.course}" --module ${m.id} once.` : ''}
NEVER edit working_claude/script/M${two(m)}.json. Your report's FIRST line is the PASS / FAIL line build_module.py printed.`
async function fixFigures(m, bf) {
  const by = new Map()
  for (const f of bf) by.set(f.slide, (by.get(f.slide) || []).concat([f]))
  const todo = [...by.entries()]
  await parallel(Array.from({ length: Math.min(FIG_FIXERS, todo.length) }, () => async () => {
    while (todo.length) {
      const [slide, fs] = todo.shift()
      await agent(fixFig(m, slide, fs), { label: `fixfig:${m.id}:${slide}`, phase: 'Build', ...MECHANICAL })
    }
  }))
  return [...by.keys()]
}

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
/* a BROKEN finding the builder can fix - not one that needs the approved script changed (owner: "SCRIPT" in its where) */
const fixable = (q) => ((q && q.findings) || []).filter((f) => f.severity === 'BROKEN' && !/^\s*SCRIPT\b/i.test(f.where || ''))

/* Module 3 is verified while Module 7 is still being written. No wasted wall-clock.
   An approved module is built and checked on Sonnet; a draft gets its script written on the session's model and
   has nothing built to check, so no QA agent is spent on it. */
/* 2.58.0 - a builder's report is checked, not trusted: no "PASS" line from build_module.py (only the course package
   failing counts as passed in a parallel build - it is judged after assembly) and a fresh agent carries the module on
   from its files, at most A.retries times (default 1). The IGF full build's Module 15 builder ended mid-build */
const passed = (r) => /\bPASS (M\d+|final)\b/.test(String(r || '')) ||
  /\bFAIL (M\d+|final) - course package \(/.test(String(r || ''))
/* 2.72.7 - a fresh agent only for a REAL stop: the builder ended mid-build or with no build answer at all. A builder that
   stopped on a build's FAIL line and listed what is left (BUILDER_CARD "Stop": the same finding three builds running) goes
   to the judges - its findings reach the one fix round anyway (the 2.72.5 run: both retries, 21 and 27 min, 28 builds,
   ended without PASS on findings the judges and the fixer got anyway) */
const answered = (r) => /\bFAIL (M\d+|final) - /.test(String(r || ''))
const stoppedShort = (r) => !passed(r) && !answered(r)
const carryOn = (m, last) => `${build(m)}

THIS MODULE WAS STARTED BY ANOTHER AGENT, WHICH STOPPED BEFORE build_module.py printed PASS. Its
build sheet, figure specs and pages are where it left them - do NOT start again from --init-build.
Run build_module.py (with --wait first if a build of it is still running), fix what it prints, until module
clean, then STOP - QA does the review. Its last report was:

${String(last || '(no report)').slice(0, 2500)}`
async function buildUntilPass(m, extra) {
  let r = await agent(build(m) + (extra || ''), { label: `build:${m.id}`, phase: 'Build', ...MECHANICAL })
  for (let k = 1; k <= (A.retries === undefined ? 1 : A.retries) && stoppedShort(r); k++) {
    log(`module ${m.id}: no build answer in the builder's report (it stopped mid-build) - a fresh agent carries it on (${k})`)
    r = await agent(carryOn(m, r) + (extra || ''), { label: `build:${m.id}+${k}`, phase: 'Build', ...MECHANICAL })
  }
  if (!passed(r)) log(`module ${m.id}: the builder stopped on a build's FAIL and listed what is left - no retry, to the judges`)
  return r
}

/* 2.65.0 (Raivis) - the gold standard (owner, 2026-10-26): 30-40 minutes a module, 20 for its fixes. A workflow has no
   clock, so the build keeps it - compile_module.py --init-build starts it, build_module.py's first PASS prints
   "TIME M01: 34 min from its starter build sheet to its first PASS - ..." - and the builder's report carries that line */
const timeOf = (r) => {
  const t = /TIME (M\d+|final): (\d+) min[^\n]*/.exec(String(r || ''))
  return t ? { minutes: Number(t[2]), over: Number(t[2]) > 40, line: t[0] } : null
}

/* ------------------------------------------------- 2.71.0 · THE 3D STEP (a module with a 3D-kit scene) */
/* the scene is the builder's spec; it is checked and photographed by a script and judged by a reviewer who did not
   build it (the 2.63.2 run: every scene passed its checks while showing "a bare pipe" and "labels as buttons below") */
const KIT3D_SCRIPTS = A.factory ? `${A.factory}/course-visuals/kit3d/scripts` : '<the course-visuals skill folder>/kit3d/scripts'
const SCENE_SCHEMA = {
  type: 'object',
  required: ['has_scene', 'ok', 'shots'],
  properties: {
    has_scene: { type: 'boolean' }, ok: { type: 'boolean' },
    shots: { type: 'array', items: { type: 'string' }, description: 'every picture path scene3d_check.py printed' },
    scenes: { type: 'array', items: { type: 'object', properties: { slide: { type: 'string' }, spec: { type: 'string' } } } },
    report: { type: 'string', description: 'what scene3d_check.py printed, word for word' },
  },
}
const REVIEW3D_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object', required: ['severity', 'where', 'what'],
        properties: { severity: { type: 'string', enum: ['BROKEN', 'POLISH', 'INFO'] }, where: { type: 'string' }, what: { type: 'string' } },
      },
    },
  },
}
const scene3d = (m, again) => `Run the 3D check of module ${m.id} - one command, in the FOREGROUND (timeout 600000 ms):

    python ${KIT3D_SCRIPTS}/scene3d_check.py "${A.course}" --module ${m.id} --json

Exit 2 ("No 3D-kit scene"): has_scene = false, ok = true, shots = [] - and stop.
Otherwise has_scene = true, shots = every "shots" path in its JSON, scenes = each scene's slide and spec, report = its output.
${again ? 'This runs after a fix round: do not change anything, only report.' : `If it found problems (a spec check, smoke3d, perf3d or the shots - "problems" in its JSON): fix exactly those in the
scene's spec (or the module's assets/kit3d_parts.js - course-visuals/kit3d/SPEC.md, PARTS.md), rebuild with
    python ${SCRIPTS}/compile/scripts/build_module.py "${A.course}" --module ${m.id} --no-course-pages
(foreground; "STILL BUILDING": the same command with --wait), and run scene3d_check.py again - at most two rounds.`}
ok = true only when its last run's JSON says "ok": true. You never judge the pictures - a reviewer who did not build the
scene does that. Write only in figures/M${two(m)}/ and modules/module${two(m)}/.${NOTES}`
const review3d = (m, s) => `You did NOT build this 3D scene. Judge it from its pictures - you change nothing.

  Module ${m.id}, course ${A.course}. The scenes: ${JSON.stringify(s.scenes || [])}
  Pictures (one per step, the scene as its slide shows it; open each ONCE, in order):
${(s.shots || []).map((p) => `    ${p}`).join('\n')}

For each scene read its slide's words first (working_claude/script/M${two(m)}.json, the screen with that id: title, text,
and the step lines) and the spec's labels and step titles. Then judge each picture:
  1 every label sits ON or right beside the part it names (not in a row of buttons, not over another part's name);
  2 the scene shows what the slide teaches - the inside, the arrangement, the flow it names - not a bare outline;
  3 the model fills its box (no small model in a big empty panel; nothing cut off at the edge);
  4 each step shows what its title and the slide's line for it say (the part lit, opened or moved);
  5 nothing contradicts the words (a part, a number, a direction).
A failure of 1-5 that a trainee would misread or not see is BROKEN; worse than it could be is POLISH. "where" = the
slide id and the picture's file name.`
const broken3d = (d) => ((d && d.review && d.review.findings) || []).filter((f) => f.severity === 'BROKEN')
/* the 3D check (a script; it fixes only what the check itself prints) and its reviewer; tag '+fix': after the fix round */
async function threeD(m, tag) {
  const s = await agent(scene3d(m, !!tag), { label: `3d:${m.id}${tag || ''}`, phase: 'Build', schema: SCENE_SCHEMA, ...MECHANICAL })
  if (!s || !s.has_scene) return null
  const r = (s.shots || []).length
    ? await agent(review3d(m, s), { label: `review3d:${m.id}${tag || ''}`, phase: 'Verify', schema: REVIEW3D_SCHEMA, ...MECHANICAL }) : null
  return { check: s, review: r }
}

/* ------------------------------------------------- 2.72.0 · THE FIGURE STEP (a module with kit figures) */
/* the IGF 2.71.0 run: every check passed and QA's one look at small review sheets rated a vent mast inside the hull, a
   "Bunkering station" of words only and pipes ending in the air POLISH - none went back. Every figure is photographed at
   projector size at every step (figure_review.py) and judged by a reviewer who did not build it, against the slide's words
   and the figure kind's must-be-true list; its BROKEN findings go back to the builder for one round */
const KIT_SCRIPTS = A.factory ? `${A.factory}/course-visuals/kit/scripts` : '<the course-visuals skill folder>/kit/scripts'
const FIGSHOT_SCHEMA = {
  type: 'object',
  required: ['has_figures', 'manifest'],
  properties: {
    has_figures: { type: 'boolean' },
    manifest: { type: 'string', description: 'the figures.json path figure_review.py printed ("written: ...")' },
    report: { type: 'string', description: 'what figure_review.py printed, word for word' },
  },
}
const REVIEWFIG_SCHEMA = {
  type: 'object',
  required: ['figures'],
  properties: {
    figures: {
      type: 'array',
      items: {
        type: 'object', required: ['slide', 'shows', 'seafarer_ok', 'findings'],
        properties: {
          slide: { type: 'string' },
          shows: { type: 'string', description: 'one sentence: what the figure actually shows' },
          seafarer_ok: { type: 'boolean', description: 'false when a seafarer would call anything in it wrong' },
          findings: {
            type: 'array',
            items: { type: 'object', required: ['severity', 'what'], properties: { severity: { type: 'string', enum: ['BROKEN', 'POLISH'] }, what: { type: 'string' } } },
          },
        },
      },
    },
  },
}
const figShots = (m, only) => `Photograph the figures of module ${m.id} for the figure review - ONE command, in the FOREGROUND
(timeout 600000 ms):

    python ${KIT_SCRIPTS}/figure_review.py "${A.course}" --module ${m.id}${only ? ` --only ${only}` : ''}

Exit 2 ("No kit figure to review"): has_figures = false, manifest = "". Otherwise has_figures = true, manifest = the
figures.json path it printed after "written:", report = what it printed. Change nothing.`
const reviewFig = (m, s) => `You did NOT build these figures. Judge each from its pictures - you change nothing.

Read ${s.manifest}. For each figure of module ${m.id} it gives the slide id, "pictures" (one per step at projector size,
1920 x 1080: step0 = the rest state, then the end of each step, in order), "words" (the slide's title and lines),
"step_titles", "kinds" (each with its "truths": what must be true in that kind of figure, IGF) and "meaning" - what the
automatic meaning checks say: "block" (a clear physical error - BROKEN unless the pictures plainly show it is right: then
say why), "note" (a possible problem - judge it in context: BROKEN only if a seafarer would call it wrong, else POLISH or
nothing) and "waived" (the builder accepted it on purpose, with a reason - BROKEN only if the reason does not hold).
Open every picture ONCE, in order.

For EACH figure: "shows" = one sentence on what it actually shows; "seafarer_ok" = would a seafarer call it right?
Then its findings:
  BROKEN - a wrong physical arrangement (a vent mast, manifold or hatch inside the hull; a tank half through the deck);
           a part the slide's words, a step title or a label name that is not drawn; a pipe, hose or line ending on
           nothing; a spray, curtain or detector attached to or aimed at nothing; a vent said to vent with no gas leaving
           it; a label floating over nothing; a row of captions with drawings under only some; a caption or panel title
           with no panel; a small drawing lost in a big empty panel; a step whose picture does not show what its title
           says; a "truths" sentence that is not true; a wrong fact.
  POLISH - right and complete, but could look better - a label a little far from its part, a pipe a few units short
           that still reads as joined, spacing. A minuscule detail is never BROKEN.
"slide" = the slide id as written in the manifest. Be concrete: the step, the part, where - a builder fixes from it.`
const brokenFigs = (r) => ((r && r.figures) || []).flatMap((f) => (f.findings || [])
  .filter((x) => x.severity === 'BROKEN').map((x) => ({ slide: f.slide, what: x.what })))
/* the figures photographed at projector size and judged; only = the slides to photograph again after the fix round */
async function figures(m, only) {
  const tag = only ? '+fix' : ''
  const s = await agent(figShots(m, only), { label: `figshots:${m.id}${tag}`, phase: 'Build', schema: FIGSHOT_SCHEMA, ...MECHANICAL })
  if (!s || !s.has_figures || !s.manifest) return null
  const r = await agent(reviewFig(m, s), { label: `reviewfig:${m.id}${tag}`, phase: 'Verify', schema: REVIEWFIG_SCHEMA, ...MECHANICAL })
  return { review: r }
}

/* one module, start to finish: built (or its script written); then its judges AT THE SAME TIME - the 3D step, the figure
   step and QA judge the same built module and none changes it (2.72.5); ONE fix round for all their BROKEN findings; then
   only what was BROKEN is judged again, again at the same time. Never a second fix round (NOTHING LOOPS, 2.72.0): what is
   still BROKEN goes on the operator's list - a 3D finding still blocks the module, as before */
/* 2.73.0 - Phase A's line for a module, and what its builder is told */
const num = (x) => String(x).replace(/\D/g, '')
const lineOf = (m) => {
  const row = ((phaseA && phaseA.modules) || []).find((x) => num(x.module) === num(m.id)
    || new RegExp(`\\bM0*${num(m.id)}\\b`).test(x.line || ''))
  return row ? String(row.line || '') : ''
}
const cleanA = (line) => /\bPASS M\d+/.test(line) || /\bMODULE CLEAN\b/.test(line)
const phaseB = (m) => {
  const line = lineOf(m)
  return line ? `

PHASE A HAS RUN (2.73.0): your module was built with no agent - --init-build's starters and placeholders, every check, the
course catalogue's picks. Its answer: ${line}
Do NOT start again from --init-build. Your brief is working_claude/visuals/M${two(m)}_VISUAL_NEEDS.md - each picture slot
still to fill (its kind, shape, real px size, the words it teaches, what it must show, the catalogue's candidates), the
figures at their starter and the 3D scenes to place - with the build's own answer. First run build_module.py <course>
--module ${m.id} --no-course-pages --auto (the sourcing pass may have found photos since), then fill what is left (a photo:
into assets/img with its _photo_meta.json record, 800 px or more; a question's picture: its answers' boxes onto the real
things), place the 3D parts, fix what the build printed, and build again until module clean. A placeholder never ships.` : ''
}
async function oneModule(m) {
  if (!APPROVED.has(String(m.id))) {
    await agent(writeScript(m), { label: `script:${m.id}`, phase: 'Build' })
    /* 2.73.0 - its photographs: the course's ONE photo pass after every script of this run is written (photos:drafts) */
    return { module: String(m.id), classification: 'AWAITING APPROVAL - script written, nothing built', blocking: false, findings: [] }
  }
  /* 2.73.0 - Phase A finished it (PASS / MODULE CLEAN): no builder, straight to the judges; else the builder's brief is its needs file */
  const time = cleanA(lineOf(m)) ? null
    : timeOf(await place(() => buildUntilPass(m, phaseB(m))))       // 2.65.0 (Raivis) - the module clock, from the builder's report
  const [d3a, fga, q] = await Promise.all([threeD(m), figures(m),
    agent(qa(m), { label: `qa:${m.id}`, phase: 'Verify', schema: QA_SCHEMA, ...MECHANICAL })])
  const b3 = broken3d(d3a), bf = brokenFigs(fga && fga.review), bq = fixable(q)
  let d3 = d3a, fg = fga, out = q
  if (b3.length || bf.length || bq.length) {
    log(`module ${m.id}: BROKEN - 3D ${b3.length}, figures ${bf.length}, QA ${bq.length} - one fix round`)
    if (bf.length) {
      /* 2.72.7: a fixer per figure (at most FIG_FIXERS at once) and the module fixer beside them, none building; then one build */
      const figs = [...new Set(bf.map((f) => f.slide))]
      await Promise.all([fixFigures(m, bf), b3.length || bq.length
        ? agent(fixAll(m, b3, [], bq, figs), { label: `fix:${m.id}`, phase: 'Build', ...MECHANICAL }) : null])
      await place(() => agent(fixBuild(m, b3, figs), { label: `fixbuild:${m.id}`, phase: 'Build', ...MECHANICAL }))
    } else {
      await place(() => agent(fixAll(m, b3, bf, bq), { label: `fix:${m.id}`, phase: 'Build', ...MECHANICAL }))
    }
    const [d3b, fgb, q2] = await Promise.all([
      b3.length ? threeD(m, '+fix') : null,
      bf.length ? figures(m, [...new Set(bf.map((f) => f.slide))].join(',')) : null,
      bq.length ? agent(qa(m), { label: `qa:${m.id}+fix`, phase: 'Verify', schema: QA_SCHEMA, ...MECHANICAL }) : null])
    if (b3.length) d3 = { check: (d3b && d3b.check) || d3a.check, review: (d3b && d3b.review) || d3a.review, first_review: d3a.review.findings }
    /* NOTHING LOOPS (2.72.0, approved by Aleksis): what is still BROKEN after the one fix round goes to the operator's list,
       never back to a builder and never failing the module again */
    if (bf.length) {
      const r = (fgb && fgb.review) || fga.review
      fg = { review: r, first_review: (fga.review && fga.review.figures) || [], for_aleksis: brokenFigs(r) }
    }
    /* 2.63.3 - QA once more after the fix (its sheets show only the screens the fix changed); never a third */
    if (bq.length) out = q2 ? Object.assign({}, q2, { first_qa: q.findings,
      for_aleksis: fixable(q2).map((f) => `QA ${f.where}: ${f.what}`) }) : q
  }
  if (out && d3) {
    out = Object.assign({}, out, { three_d: d3 },
      broken3d(d3).length || (d3.check && !d3.check.ok) ? { blocking: true } : {})
  }
  if (out && fg) {                                   /* the figures' left-overs are the operator's list, not a module failure */
    const left = (fg.for_aleksis || []).map((f) => `FIGURE ${f.slide}: ${f.what}`)
    out = Object.assign({}, out, { figures: fg, for_aleksis: ((out.for_aleksis) || []).concat(left) })
  }
  return out && time ? Object.assign({}, out, { time }) : out
}

/* at most A.wave BUILDS at once (default: all) - each build runs hidden browsers, so on one PC 3 keeps it from being pinned
   at 99 % (the IGF full build ran in waves of 3). Raivis's 2.65.0 and 2.71.0, merged: the biggest module first (build_order.py's
   cost), and a rolling pool - the next build starts the moment one ends. Only a build holds a place: the builder (and its
   retry), a fix round that builds, the one build after the figure fixers; the judges and QA run beside the builds (a QA
   agent runs no figures stage). The waves waited for their slowest member (2.63.2: 95 / 54 / 41 / 33 / 39 min; 2.63.3
   M01-M03: 114 min, M02 alone at the end) */
const WAVE = Math.max(1, A.wave || A.modules.length)
let free = WAVE
const waiting = []
async function place(work) {
  while (free === 0) await new Promise((go) => waiting.push(go))
  free--
  try { return await work() } finally { free++; const next = waiting.shift(); if (next) next() }
}
log(`build order, biggest first: ${ORDER.map(({ m }) => `M${two(m)}${COST.has(String(m.id)) ? ` (${COST.get(String(m.id))})` : ''}`).join(', ')}`
  + (WAVE < A.modules.length ? ` - ${WAVE} builds at a time, the next starting as one ends` : ''))
const approvedIds = ORDER.filter(({ m }) => APPROVED.has(String(m.id))).map(({ m }) => m.id)
const [phaseA] = approvedIds.length
  ? await parallel([
    () => agent(phaseAPrompt(approvedIds), { label: 'phase-a:modules', phase: 'Build', schema: PHASE_A_SCHEMA, model: 'sonnet', effort: 'low' }),
    () => agent(photoPass('beside Phase A, while the approved modules build with no agent'),
                { label: 'photos:course', phase: 'Build', ...MECHANICAL }),
  ])
  : [null]
const results = new Array(A.modules.length).fill(null)
await parallel(ORDER.map(({ m, i }) => async () => {        // each asks for its place in this order: biggest first
  try { results[i] = await oneModule(m) } catch (e) { log(`module ${m.id}: ${e && e.message ? e.message : e}`) }
}))
const drafted = ORDER.filter(({ m }) => !APPROVED.has(String(m.id))).map(({ m }) => m.id)
const draftPhotos = drafted.length
  ? await agent(photoPass('after this run wrote the scripts of modules ' + drafted.join(', ')
      + " - their photographs are found while the operator reads them, not on the build's clock"),
    { label: 'photos:drafts', phase: 'Build', ...MECHANICAL })
  : null

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

compile_course.py (2.83.0) also writes modules/_course_shell/ilo_coverage.json - the ILO map the admin panel shows - and
prints, among its lines, which Sub-ILOs are taught or checked nowhere and any tag no row owns: report those lines word
for word, they are findings for the cross-check, never yours to fix.

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
  /* 2.65.0 - each built module's minutes to its first PASS against the gold standard (30-40), and which went over */
  gold_standard: {
    target: '30-40 min a module, 20 min for its fixes',
    minutes: results.filter((q) => q && q.time).map((q) => ({ module: q.module, minutes: q.time.minutes })),
    over: results.filter((q) => q && q.time && q.time.over).map((q) => q.module),
  },
  next: blocking.length
    ? 'Blocking findings. Fix them in the named modules, then run compile_course.py and check_course_package.py again.'
    : 'Approve every script still awaiting approval and run pass 2 again (approved modules are rebuilt '
      + 'from their scripts, unchanged ones stay the same bytes). The course pages are assembled above; then '
      + 'the handout, the run content, and course-tablet-publisher.',
}
