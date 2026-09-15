/* NOVIKONTAS Course Factory — read the programme, then build every module at once.
 *
 * Pass this to the Workflow tool as `script`, with `args` set to:
 *
 *   { course: "<absolute path to the course folder>",
 *     programme: "<path to the approved programme>",
 *     kb: "<path to the docling knowledge base>",
 *     modules: [ { id: "m1", title: "...", minutes: 240, theory: 200, practical: 40 }, ... ] }
 *
 * `modules` is deliberately an INPUT, not something the script discovers. The reader
 * produces the split, the owner approves it at the gate, and only then is this run with
 * the approved table. That is the whole point of the gate — see orchestration/GUIDE.md.
 *
 * Run it in two passes:
 *   pass 1  omit `modules`  -> the reader runs, writes the two maps, and STOPS.
 *   pass 2  with `modules`  -> the fan-out, with QA pipelined behind each module.
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
  required: ['modules', 'total_minutes', 'language'],
  properties: {
    language: { type: 'string' },
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
The knowledge base:      ${A.kb}
The course folder:       ${A.course}

Work alone with those three. Produce TWO FILES in the course folder — nothing else,
and no slides:

  MODULE_MAP.md   module -> official topic numbers -> allocated minutes (theory /
                  practical) -> what the module teaches -> what it checks -> whether
                  it needs a facility. The minutes column MUST sum to the programme
                  total; run hours/scripts/check_hours.py and read its output.

  ILO_MAP.md      every Main ILO and Sub-ILO, per module, with HOW each one is met:
                  taught / practised / assessed, against a named screen, task or
                  practical. One row per outcome. Main ILOs are copied VERBATIM (L2).
                  Any Sub-ILO you re-express is marked PROVISIONAL.

Detect and state COURSE_LANGUAGE (L6). Raise every UNKNOWN rather than inventing an
hour, a pass mark or a citation, and never web-search during intake.

Then return the module table as JSON. Do not build anything.`

const plan = await agent(READ, { label: 'read:programme', phase: 'Read', schema: MAP_SCHEMA })

if (!A.modules || !A.modules.length) {
  /* The gate. The owner approves the table before anything expensive happens. */
  return {
    stopped_at: 'GATE',
    why: 'The module split and the minutes are the expensive things to get wrong. '
       + 'Review MODULE_MAP.md and ILO_MAP.md, then re-run with args.modules set to the approved table.',
    proposed: plan,
  }
}

/* ------------------------------------------------- 1..N · BUILD, WITH QA BEHIND */

const build = (m) => `Invoke ${SKILL} and follow it. Build ONE module.

  Course folder:   ${A.course}
  Your module:     ${m.id} — ${m.title}
  Your minutes:    ${m.minutes} total (${m.theory} theory / ${m.practical} practical)

Read ONLY your own rows of ${A.course}/MODULE_MAP.md and ${A.course}/ILO_MAP.md, plus
the source extracts they name. Do not read the whole knowledge base.

YOU MAY WRITE ONLY INSIDE  ${A.course}/modules/${m.id}/
Never the registry, never course.json, never the handout, never another module. Those
are assembled afterwards by one process, because two agents writing one file is a lost
write that no test catches.

Your minutes are fixed and are not negotiable — anything that will not fit becomes
self-study, and you record it so the handout can pick it up (L1).

The visual layer is routed, never improvised: course-module-ui owns the look,
course-visuals owns what the picture should be. Every TOPIC screen leads with a figure
(L23) — search the source files and knowledge base first, then the internet for a real
photograph, then author or generate. A screen that honestly needs no figure declares it
with data-novisual="<reason>". Where an image needs generating and you cannot produce
it, write the brief to _visual_briefs/ and keep going: the module is finished as far as
it can go, and the handoff is written at the end.

Report what you built, every honesty marker with its source, the achieved Track A
buckets and Track B ratio, and what you moved to the handout.`

const qa = (m) => `You did NOT build this module. Check it.

  Module:  ${A.course}/modules/${m.id}
  Against: ${A.course}/MODULE_MAP.md and ${A.course}/ILO_MAP.md (its rows only)

Run the deterministic checks and READ their output — check_hours, check_balance,
check_syllabus_coverage, verify_links, audit_navigation, crosscheck_tasks,
check_slide_text, check_visual_first, check_visuals, check_assets, audit_ui --strict,
and classify_module.py.

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
  * every outcome in ILO_MAP.md is taught somewhere, and no outcome is claimed twice
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
    : 'Assemble: registry, course.json, the handout, the run content — one process, not an agent each. '
      + 'Then course-tablet-publisher.',
}
