---
name: course-factory
description: >
  Use for a WHOLE accredited course on the NOVIKONTAS tablets - building one from an approved
  programme, or UPGRADING an existing one. Trigger on "make a new course", "build course X like
  GAS BASIC", "add a course to the tablets", "how many hours does this module get", "is this 1:1
  with the programme"; and equally on RETROFIT requests about material that already exists:
  "redesign Module 1 using the Course Factory", "upgrade this existing module", "make my existing
  module like GAS BASIC", "make these modules presentable", "make this module production-ready",
  "improve the existing presentation / course UX", "modernise this existing course", "apply Course
  Factory to this module", "make this module more visual and interactive", or the same intent in
  Latvian or Russian. In retrofit the course CONTENT is locked and the existing DELIVERY
  implementation is not - screens, layout, visuals, animation and interaction are rebuilt to the
  canonical product, and the operator never has to name a skill, a validator or a folder. Owns
  mode selection, the accredited-hours law, ILO immutability, the content-lock/delivery-freedom
  law, COURSE_LANGUAGE, and the contract for adding a course to both terminals. NOT the deck's
  screen craft (course-module-ux), NOT the visual layer (course-module-ui), NOT what representation
  teaches a concept (course-visuals), NOT trainee task screens (course-task-ux), and never what a
  course teaches.
---

# Course factory — an accredited programme becomes two tablets

**v1.2 (2026-09-30) · Maintained by Raivis · part of the `course-factory` plugin, shared with colleagues through the marketplace**

## Every reply to the operator — human, and in three parts (L25, owner 2026-10-01)

*"Every response needs to be humanized and understandable - by points: what's done, what's next, what to check
now - understandable for a person who knows zero about IT and all these terms."*

Every message the operator reads - in the chat, at every STOP, after every step - is written for someone who knows
the sea and the course, and nothing about computers. It has these three parts, as short points, in the operator's
language:

| | English | Latviešu | Русский |
|---|---|---|---|
| what was done, and what it means for the course | **Done** | **Izdarīts** | **Сделано** |
| what to open or look at now, and exactly where (the full path, and what it opens in) | **Check now** | **Pārbaudiet tagad** | **Проверьте сейчас** |
| what happens next, and what the factory needs from them, if anything | **Next** | **Tālāk** | **Дальше** |

- **Everyday words.** No *script, JSON, commit, push, repo, plugin, render, flag, hash, schema, validate, pipeline,
  build, folder tree* - say what it is: *"the file that holds the module's words"*, *"save and publish the factory"*,
  *"the check found nothing wrong"*. A technical word that truly cannot be avoided gets its plain meaning beside it,
  once. The maritime terms stay exactly as professional as they are (L28) - this is about computer words only.
- **Short.** A few points per part, one idea a point. Numbers as the operator counts them: *"23 modules"*, *"80
  minutes"*, not file sizes or test counts unless they asked. Test results in one plain line: *"all checks passed"*.
- **Nothing to decode.** A question is a choice with options (the pop-up, L31), not an essay. A problem always says
  what to do about it (the five parts below). Commands the operator must run are given ready to copy, with one
  sentence on what they do - never as the only explanation.
- **Offer, don't instruct.** If the factory can do it, say *"tell me and I will"*.

`knowledge/plain-language.json` → `every_reply` holds the same rule for the checks.

**The acceptance test.** Someone who has never seen the course opens the instructor terminal,
types their ID, picks the module, presses **Start**, and presses **Next** to the end — and a real
accredited class gets taught, in the minutes the approved programme allows, with the trainees'
tablets carrying every task the screens announce.

This skill is the **entry point** for that delivery target. It decides mode, runs the gate, and
routes. It does not itself write screens, tasks, or content.

---

## The operator's request wins — L26

**"The style" means the Novikontas brand system only** — brand colours, typography, logo use, and
the shell, tokens, components, navigation and tablet system it is built into. Anything a colleague
asks for about content, structure, emphasis, number of slides, examples, visuals, tasks or wording
is **done**: never refused, never watered down, never quietly ignored as "not in the style". Their
request in chat is the explicit authorisation L18 asks for, and it reaches expert-edited regions
too (L24 protects an expert's change from the factory, not from the operator).

Only five limits are hard: **the brand · the programme and its Main ILOs (L1, L2) · the official
hours (L1, L3) · no source, no maritime claim (L4) · the offline tablet (L6)**. A fact the operator
states is a source — use it, record it as theirs, and list it in that module's content-script review (L29). When a request truly hits a hard limit: one
or two plain sentences why, the closest option that works, and then do that. Every other "never"
in this factory governs the factory's own choices, not the operator's requests.

## Owner decisions in force — Phase 5

Decided 2026-09-30. **Where an older rule anywhere in this factory disagrees with a row below, the
row wins** — even before its step has been built out. Full text: `references/laws-in-full.md`.

| | The rule | Built out in |
|---|---|---|
| **L27** | Three test levels, all on the **trainee tablet**: self-checks and the module check show the trainee **their own score** — it is for them and does not count; the **final assessment is the only graded test**. Every task opens only when the instructor opens it (L35); the instructor sees done / not done and the result as information, never pass/fail or red | step 6 |
| **L28** | Course type `NEW_ENTRANT` or `EXPERIENCED` is declared at intake and shapes the build (new entrants: more explanation, more screens, more worked examples). **Never easier names** — every course uses the professional terms used on board and in the regulations, explained so a new entrant understands them and can explain their actions at sea (owner, 2.18.2). Every instrument and simulator in the IMO model course is assumed available — never asked | steps 2, 7 |
| **L29** | Before any HTML, a word-for-word **content script** per module is approved by the operator; the slides then say exactly that. Facts the operator stated are listed there once per module, marked *operator-stated*, so they are checked before HTML — see *Stage 3* below | now |
| **L30** | **Module 1 is a pilot**, built by five roles and approved before any other module is built | step 10 |
| **L31** | Ask like a colleague: real expert questions batched as **one pop-up with options** at the next STOP, then carry on. No "needs SME review" spam. Honesty markers live in `factory-notes.md`, never on a slide, never a reason to stop; "next" at a STOP ratifies what it showed | now |
| **L32** | `COURSE_STATE.md` updated at the end of every stage; every operator correction in `FEEDBACK_LOG.md`; a pattern file offered when the operator is happy — see *The course remembers* below | now |
| **L33** | Pictures: KB → old course → source files → internet → authored → generated; keep legit old schematics; **every picture in the knowledge base and the old course is usable as it is** (credited where known, listed); what is missing is **searched on the internet and downloaded** into the course folder, the download list confirmed once per module (owner, 2.19.0); equipment a trainee must recognise is **never** an AI image — schematic plus the "photos to take at Novikontas" list | step 8 |
| **L34** | **One module per programme topic** — in the programme's order, with the programme's hours (GAS BASIC: 22 teaching modules). The programme's final-assessment topic is the **last module, and the assessment only**: no slides, no teaching. Topics are never merged or split. An academic hour is the programme's; at Novikontas 40 min when it is silent | now (2.17.0) |
| **L35** | **Two tablets.** The slides run on the instructor tablet, mirrored to the classroom screen; the notes stay on the instructor's panel. Tasks are **only** on the trainee tablet. At task time the slide only says a task starts now and what it is about, and the instructor's panel has one button, **OPEN TASK**; the task then opens on every trainee tablet by itself. No task list, no browsing, no "all tasks" or "back to tasks" button | now in the script and architecture; the app's change list in step 6 |
| **L36** | **Enough theory before any task.** A slide carries the teaching itself, not a headline; the notes carry what the instructor explains; a module's words fill its minutes; a self-check comes only after a block of new theory; every answer is taught before its task opens. Floors: `knowledge/theory-rules.json`, checked on the content script | now (2.17.0) |
| **L37** | **Every slide leaves room for its picture** and names it: the kind (photograph, schematic, cutaway, chart, step / flow / process animation, interactive diagram, 3D model, 3D scan, video, AI illustration ...), what it shows, the layout - and **who makes it**: the factory, the image/video generator (context only), the sources, **Novikontas** (a photo, a film, a phone 3D scan) or outside help. 40+ min of theory: something that moves, turns or can be explored. `knowledge/media-and-tasks.json` | now in the script and architecture; built in steps 8-9 |
| **L38** | **Tasks are varied and hands-on** - 14 ways of answering, none typing: choose one / all, choose-and-justify, order, match, sort, complete the sentence, tap the place, label the drawing, find the hazards, read the instrument, set the value, operate the panel, scenario. A self-check uses 2+, a module check 3+; "choose one" at most 40 %; one hands-on question per module | now in the script and architecture; built in step 6 |
| **L39** | **Who tests where.** The build makes every file ready for the tablet system; a colleague gets **only the HTML**, to check in their own browser; **the real-tablet test is the owner's, at the end**. Instructor notes are short points in `instructor_notes/M01_INSTRUCTOR_NOTES.md`, for the panel - never on a slide (2.18.1). Pictures have no quota: every chance to show the theory is taken, and the picture floors are suggestions | now (2.18.1) |
| **L40** | **The factory works in `course\`** beside the operator's material: the folder given is the master folder (source_files, knowledge base, old course - read only); everything the factory makes goes into `course\` next to them. `scripts/workspace.py`; every tool accepts either folder | now (2.19.0) |
| **L42** | **Trainee-tablet tasks are modern, exciting, and usable with zero tablet experience** - a first *try the tablet* screen; tap and drag only (drag also tap-then-tap); an animated hand shows each new gesture once; big controls (56 px), big text; instant, alive feedback; real equipment in 3D and working panels; forgiving, no timers, no error messages. `course-task-ux` §0 | built in step 6 |
| **L43** | **Every module in its own folder** - `course\modules\M01_<title>\` holds everything it needs (presentation, tasks, instructor files, every asset and script), reaches nothing outside it, fetches nothing; `START_HERE.html` opens the presentation straight away; `START_HERE_EXTENDED.html` has a button for the presentation, every task, the module plan, the notes. `scripts/check_module_folder.py` | built in steps 6-10 |
| **L41** | **The old course is the foundation.** Read it whole at intake (`scripts/old_course.py inventory`, and `images` for its pictures); at the Stage 2 STOP every module says what it **keeps**, what it **modernises and makes digital**, and what it **adds** | now (2.19.0) |

Theory is delivered as active learning (L5): self-check, **explain-then-reveal** (no typing),
predict-then-reveal, worked example then own attempt. More practice than theory; theory never removed.

## The course remembers — L32

`scripts/course_memory.py` runs it; the templates are `templates/COURSE_STATE.md`,
`FEEDBACK_LOG.md` and `COURSE_PATTERN.md`. All three stay in the course folder and never ship.

- **Every session starts by reading `COURSE_STATE.md`** if the course folder has one, and never
  re-asks or re-decides what it lists under *Decided*. A new course: `course_memory.py start`.
- **At every STOP**, update it: stage, what was approved, open questions, next step, file map. Then
  `course_memory.py check` — it says whether a new session could resume from it.
- **Every correction the operator makes** goes into `FEEDBACK_LOG.md` straight away, in their words,
  with what changed; a fact they state is marked *operator-stated* (L29).
- **At the end, when the operator says they are happy**, offer a pattern file. `draft-pattern` drafts
  it from the log; **show it to the operator in plain language**, and let them change or remove any
  point. Save it only when they approve: `approve-pattern --by "<name>"`, which refuses until it
  names the course, the course type and who made it. The owner copies it into
  `resources/course-patterns/`, and every colleague gets it with the next update.
- **A new course** lists the approved patterns (`course_memory.py patterns --course-type <type>`)
  and reads the ones that fit. They are guidance, never rules, and never above the current
  operator's request. Drafts are never read.

---

## Mode first, then read one lane

| Mode | You are asked to | Read |
|---|---|---|
| **plan** | turn an accredited programme into a module set with hours that add up | `hours/GUIDE.md` |
| **retrofit** | upgrade, redesign, modernise or "make presentable" material that **already exists** | `retrofit/GUIDE.md` |
| **preview** | let a colleague SEE the course — "how does it look", "let me review it", "open it in the browser" | `course-tablet-publisher` → `references/preview-and-approval.md` |
| **edit** | make the content or structure change the operator named — add, remove, split, merge, reword, keep, more examples. **Do it** (L26) | `retrofit/knowledge/routing.json` § edit_triggers |
| **restyle** | make one **narrow** cosmetic change and nothing else | `retrofit/knowledge/routing.json` § restyle |
| **ship** | put an **approved** course onto the trainee and instructor terminals | `tablet/GUIDE.md`, and `course-tablet-publisher` owns the act |
| **audit** | check an existing course against the programme and the terminals | `coverage/GUIDE.md`, then both lanes' verify sections |
| **orchestrate** | build a WHOLE course from a knowledge base, with one agent per module | `orchestration/GUIDE.md` |

`retrofit/knowledge/routing.json` is the authority on which mode a free-form request selects, and
on telling **retrofit** apart from **restyle**. Match the operator's *intent*, never a phrase — a
colleague in Cowork types "Redesign Module 1 using the NOVIKONTAS Course Factory" and that has to
be enough, with no skill name, validator name, folder path or git in it.

Restyle needs **both** a narrow cosmetic target *and* a scope limiter: "only change the colours" is
a restyle; "change the colours and make it like GAS BASIC" is a retrofit. When someone asks for a
restyle, give them a restyle — say in one line what a full retrofit would additionally do, and
stop. Doing more than was asked is not generosity.

Never load a lane the mode does not need. `hours/` answers "how long may this be"; `tablet/`
answers "where does it live and how is it wired"; `coverage/` answers "is everything the programme
**and the model course** ask for actually taught"; `retrofit/` answers "what of this existing
module survives, and what gets rebuilt". They never run together — except that a retrofit still
obeys the hours law, so `retrofit/` reads `hours/` for Track A and nothing else.

`orchestration/` is the only lane that is about the *run* rather than the course, and `coverage/`
exists because exact hours and perfect wiring still cannot see a missing outcome. What each is
for, and the one rule that keeps a parallel build from losing work: `references/routing-notes.md`.

### Deliberately outside this bundle — point at these, never copy them

| Concern | Owned by |
|---|---|
| Screen craft, one-page architecture, deck measurement, run-script generation | `course-module-ux` |
| **The visual layer** — palette, typography, light/dark-photo modes, header band, cards, pills, takeaway, semantic status colour | **`course-module-ui`** |
| **What representation teaches a concept** — photo, schematic, animation, chart, cutaway, or no visual at all; the asset pipeline, provenance and rights | **`course-visuals`** |
| Trainee task screens — answering, navigation, typed input, completion | `course-task-ux` |
| Publishing a finished course to the two terminals and the shared repository | `course-tablet-publisher` |
| Course intake — course type, accreditation, equipment, regulations | `novikontas-course-intake` |
| The course plan document, competence matrix, session plan | `novikontas-course-plan` |
| `COURSE_START.json` contract, honesty markers, traceability tiers, gap report | `novikontas-course-start` |
| ILO wording, verbs, constructive alignment, assessment design | `novikontas-pedagogy-toolkit` |
| Exercise forms, handouts, written tests, decks as pptx | the `novikontas-*` material skills |
| Visual identity — logo, colour, type | `novikontas-brandbook` |
| Getting text and figures out of source PDFs | the operator's knowledge base — Course Source Processor or docling — read only through `kb/scripts/kb_tool.py` (`kb/GUIDE.md`) |

If a question belongs to a row above, say so and point. Do not re-derive it here.

### When an organisation skill is not installed

The `novikontas-*` skills are **not** part of this plugin and are not guaranteed to be present.
Owner decision **D-3**: use the organisation skill when it is installed; otherwise use the minimal
fallback in **`org/ORG_DEPENDENCIES.md`**; either way record which route was taken in
`factory-notes.md` §0.

Three are **blocking** — `novikontas-pedagogy-toolkit`, `novikontas-handouts` and
`novikontas-course-start` own required build steps and have a fallback each. The rest are pointer
rows: name the skill that would have owned the question, answer it within this factory's own rules,
and say so. Never paraphrase an absent organisation skill from memory and present it as its content.

---

## The brief — a call and a folder, and that is the whole contract

> **The operator calls the factory and gives a folder. Nothing else is required of them.**
> Everything after that is either derived, or found inside that folder. They type a correction
> only when they want something other than what the factory would do on its own.

That is the acceptance test for this section. A colleague who types

    Redesign this module using the NOVIKONTAS Course Factory.
    C:\courses\Module_04

has given a complete brief. No skill name, no validator, no script, no flag, no folder layout,
no module split, no screen count — and none of those may be asked back.

**Look in the folder before asking anybody anything.** The programme, the sources, the existing
module, the expert's notes and the factory's own build record are usually all in there or one
level up, and a question whose answer was sitting in the folder is the fastest way to teach an
operator that this tool is hard work.

**Stage 1 — intake.** `knowledge/intake.json` is the authority: what to look for first, the
questions, and what to record. In order:

0. **The folder given is the master folder** (L40): work in `course\` beside the material - `python scripts/workspace.py
   <folder>` says where. Never write into `source_files\`, the knowledge base or the old course.
1. **Look in the folder** for the programme, the IMO model course, the knowledge base, the old
   course; propose the course type from the programme. The course language is always English.
   **Read the old course whole** (L41): `python scripts/old_course.py inventory <old course> --course <folder>`
   and `... images ...` - it is the foundation the architecture is planned from.
2. **Sort the sources** — `kb/scripts/kb_tool.py sources <kb> --course <course>` (read `kb/GUIDE.md`):
   exact copies and .doc/.docx pairs are settled without asking; each publication found in more than
   one edition becomes a "which edition is current?" question.
3. **Ask what is still missing — once, as pop-up questions with options** (the ask-question tool; up
   to four per pop-up, most important first): the programme if not found (the one blocking answer),
   the knowledge base, the old course (a local folder; a Drive link only if it reads reliably), the
   course type (`NEW_ENTRANT` / `EXPERIENCED`, the programme's pointer first as *Recommended*), the
   model course only if not found, the edition questions, and — in retrofit, only
   when `detect_expert_edits.py` says `nothing-to-go-on` — whether anyone edited it by hand (L24).
4. **Record** it in `_factory/intake.json`, editions via `kb_tool.py decide`. Nothing is asked twice.

Every instrument and simulator in the IMO model course is **assumed available** (L28) — never asked.
Never ask the module split, screen count, task codes, pass marks, file layout or which lane to
load: those are derived. Never web-search during intake; `UNKNOWN` means asked and not known.

**Corrections are the operator's only other input, and they arrive in their words.** "Too much
text on screen 4", "keep the old pump drawing", "this should be two screens" — act on them, and
do not turn a correction into an interview.

---

## The laws — the operative rule of each

These are not preferences; each is here because breaking it cost real rework. Numbered as in
`docs/FACTORY_LAWS.md`, the one numbering the whole factory uses.

> **The full text of every law — its reasons, its cases and its edge rules — is in
> `references/laws-in-full.md`.** Read the law in full before bending, questioning or changing
> one, and whenever an operator's request seems to collide with it.

**L1 · The approved programme is law, and minutes are its units.**
`hours/knowledge/hours-rules.json` is the authority. An academic hour is whatever the programme
says (GAS BASIC: 40 min) — never assume 60. Every module's built teaching time equals its
allocated minutes **exactly**; anything that will not fit becomes self-study in the handout.
Run `hours/scripts/check_hours.py` before believing any plan.

**L2 · Main ILOs are untouchable.** Main ILOs and the approved programme are copied
**verbatim** — never edited, renumbered or "improved". Sub-ILOs may be re-expressed; a
re-expressed Sub-ILO is `PROVISIONAL` until ratified and never renumbered in anything a trainee
sees. The programme governs; an IMO model course is guidance.

**L5 · Two tracks, and only one of them is yours.** Track A — the programme's theory/practice
allocation — is fixed: declare each block's bucket with `data-track` and run `check_balance.py`.
Track B — learner-active minutes — is designed: aim for 80 %, declared with `data-active`. Where
the practical share is small, the theory hours are delivered as active learning; a theory block
with no trainee activity in it is a defect. Never reach the target by renaming screens.

**L7 · Nothing is useless until you have grepped for what depends on it** — its id, class, label
and filename, across both terminals, the course tree and every generated script.

**L18 · Content is locked. The delivery implementation is not.**
`retrofit/knowledge/content-lock.json` is the authority. Locked, needing explicit authorisation:
technical meaning, programme requirements, ILOs and Sub-ILOs, official hours, assessment intent,
intended practical exercises, course terminology, source-supported facts, COURSE_LANGUAGE. Free:
screen count and order, HTML, layouts, density, visuals, animation, interaction, navigation,
CSS/JS, composition. An existing visual is evidence of a teaching decision — preserve the
decision, rebuild the implementation. The operator's request in chat **is** the explicit
authorisation (L26).

**L24 · Where the expert has already changed something, that change is content.**
`retrofit/knowledge/expert-edits.json` and `retrofit/scripts/detect_expert_edits.py`. Decided from
evidence — a marker the expert left, the factory's build record, a commit the factory did not
author — and if none exist, **ask**. A protected region is restyled, never rewritten; where it
breaks another law, name the law and propose the fix in the report — do not apply it. It is
protected from the factory, never from the operator: when they ask for a change there, make it (L26).

**L21 · The production Android application is a publish target, not a workspace.** READ ONLY
without a person's own approval for that named course and version: *"Approved. Publish this
course to the NOVIKONTAS training app."* Review happens in the colleague's own folder
(`course-tablet-publisher` → `preview.py`); `publish.py --publish` refuses without `--approved-by`.

**L19 · COURSE_LANGUAGE is declared, and the operator's language is not it.** Detect it, state it
back in one line, lock it — in plan and retrofit alike. Course-facing material stays in it unless
translation is explicitly requested; the chat report and `factory-notes.md` follow the operator.
`retrofit/scripts/check_language.py` is the drift check. **Every Novikontas course is in English**
(owner, 2026-09-30) - COURSE_LANGUAGE is English and is never asked.

**L25 · The person reading this does not work in IT.** Every reply has three parts - **Done · Check now · Next** -
in everyday words (see *Every reply to the operator* at the top). `knowledge/plain-language.json` is the
authority; `scripts/check_plain_language.py` enforces it. Every problem message carries all five:

| | |
|---|---|
| **What is wrong** | one sentence, in the words of the course, not of the software |
| **Where it is** | the full path from the drive letter, plus the human landmark — which module, which slide, which heading |
| **How to see it** | the literal steps. Double-click what, opens in what, what appears |
| **What to do** | the fix in steps — and if the factory can do it, offer: *"tell me to fix it and I will"* |
| **How they know it worked** | what they will see afterwards. Never *"run the check again"* as the only proof |

This is not dumbing down: the maritime content stays exactly as technical as it is; what changes
is the language about computers and this tool. Offer to do the work before explaining how they
could.

---

## The gate — approved before anything is built

Changing a table row is free. Changing eight built modules is not. This is **Stage 2 → STOP**, and
the operator reviews it as **one page**:

    python scripts/make_architecture_page.py --course <course folder>

It reads `programme.json` and `architecture.json` (and `plan.json`, optional) from the course folder and writes
`ARCHITECTURE_REVIEW.html` — one file that opens with a double-click and prints to PDF. On it:

| | |
|---|---|
| **Modules** | **one per programme topic** (L34), in the programme's order: the topic and its sub-topics word for word → theory / practice → minutes → where they go (slides, self-checks, module check, practice); the last module is the final assessment only; the total checked against the programme's own total row (L1) |
| **Tablets** | how the course runs: slides on the instructor tablet, tasks only on the trainee tablet, opened with OPEN TASK (L35) |
| **Main ILOs** | exactly as the programme writes them, in COURSE_LANGUAGE (L2) |
| **Sub-ILOs** | every one beside the programme's own wording, marked **kept / re-expressed / added**, with the reason — the operator's "next" ratifies them |
| **Per module** | where theory is taught as activity (L5) · practical tasks and their equipment (L28) · self-checks — only where the theory time allows one (L36) — and the module check: the trainee's own score, not counted (L27) |
| **Final assessment** | graded, with the programme's pass mark |

Programme text appears verbatim in the programme's own language, module titles in COURSE_LANGUAGE; the headings and explanations are in the
operator's language (`architecture.json` → `operator_language`: `en` / `lv` / `ru`,
`knowledge/page-labels.json`). Run it with `--check` first: anything the page would flag — hours
that disagree, a Sub-ILO change without the programme wording, a graded module check — is fixed or
shown at the top. Markers stay in `factory-notes.md` (L31). Nothing is built until the operator
says "next"; then record it in `COURSE_STATE.md` (L32).

## Stage 3 — the content script, approved before any HTML (L29)

`script/GUIDE.md` is the lane; `scripts/content_script.py` does it. Per module, the whole lesson in
teaching order, shown on the two tablets it runs on (L35): **part 1, the instructor tablet** — every
slide's exact words, planned picture, minutes and instructor notes, and a *task starts* slide with
OPEN TASK wherever a task begins; **part 2, the trainee tablet** — every task, one question per
screen, with its answers, correct answer and feedback, ending on the trainee's own score. The
operator-stated facts are listed once. The operator gets a review page (prints to PDF) and a **Word file**; they correct by
typing, by Word comment or in the chat.

**Every correction is shown before it is applied.** `read` / `propose` only print what was
understood and leave it pending; show that list, and `apply --confirmed` only after the operator says
yes. The theory check (L36 — thin slides, thin notes, words that do not fill the minutes, a self-check
after too little theory, an answer not yet taught, a task written onto a slide) and the slide-text
check (L22) run on the script first, and their findings head the review page; every question shows
the slide that teaches its answer;
approval is refused while a must-fix one stands, unless the operator approves `--despite-findings`.
Approval is `approve --by <name>`; any later change makes it a draft again. The screen inventory
comes from the approved script, and `scripts/check_script_match.py` proves the built module says
exactly those words.

## Build order

`knowledge/build-order.json` is the authority. Read it; it names the owning skill for each step
and what each step must not start without.

The shape, for orientation only (the file wins if this line ever disagrees with it): programme →
model-course syllabus → knowledge base → ILO map → module split → **gate** → per-module screen
inventory → **visual system** → **visual plan** → tasks → screens → handout → assessment → module
plans → terminals → verify.

Three orderings that are not negotiable, all three learned by getting them wrong:

- **Screen inventory before any screen exists.** `course-module-ux` owns that gate.
- **The visual system before any screen exists.** `course-module-ui` owns it, and for a new
  module it is a **required** step, not an optional polish pass — see below.
- **Task pages before the deck announces them.** A screen that announces `T3` when the tablet
  has no `T3` is the worst failure in the room, and it is only caught by the three-way
  cross-check in `tablet/`.

### The visual layer is routed, never improvised

When a new module reaches visual production, **route it to `course-module-ui`** — it owns the look,
and this skill restates none of it. Its `scripts/design_system.py install` copies the style files
(never read them); its `references/vocabulary.md` is what to read. GAS BASIC **Module_01 is the canonical visual reference** for the look, and
**not** a template: there is no canonical screen count, and low visible density is not low
learning depth. `build-order.json` step 8, `no_fixed_slide_count` and `density_is_not_depth` are
the contract; the reasoning is in `references/routing-notes.md`.

---

## Honesty markers

One set, identical to the rest of the family (`novikontas-course-start` owns the definitions):

| Marker | Means |
|---|---|
| `UNKNOWN` | Asked, operator did not know. Record that it was asked. |
| `PLACEHOLDER` | Structure right, real content missing. |
| `PROVISIONAL` | Content exists but depends on something unapproved — every re-expressed Sub-ILO, every pass mark not yet ratified. |
| `[VERIFY: <what to check>]` | Asserted from a source this skill could not confirm. Always carries its payload. |

Never invent regulatory content, hours, pass marks or citations. Every marker must appear in the
companion file — a marker used and never reported is the failure this rule exists to stop.

---

## Verify before reporting done

Run these, read the output, then report. A green exit is not proof the work happened — inspect
the line for the thing you changed. **Why each check exists, and what got through without it:
`references/verify-in-full.md`** — read it at sign-off.

1. `hours/scripts/check_hours.py` — minutes match the programme
2. `coverage/scripts/check_syllabus_coverage.py` — every **itemised outcome** of the model course is taught
3. `tablet/scripts/verify_course.py` — structure, counts, check→hand-off order
4. `tablet/scripts/verify_links.py` — every link resolves in the **merged** asset root
5. `tablet/scripts/audit_navigation.py` — every page is **reachable** and has a way back
6. `tablet/scripts/crosscheck_tasks.py` — deck ↔ run script ↔ tablet manifest agree
7. `course-module-ux`'s measurement lane for the screens themselves
8. `course-visuals/scripts/check_visuals.py` and `check_assets.py`; then, in the page,
   `GBVerifyFigures.run()` and `await GBVerifyFigures.motion()` (L20); then
   `course-visuals/review/GUIDE.md`. Nothing at `RIGHTS_REVIEW_REQUIRED` may ship.
9. `course-visuals/scripts/check_visual_first.py <module> --strict` (L23), then
   `course-visuals/scripts/write_visual_handoff.py <module>`
10. `course-module-ui/scripts/design_system.py check <module>`, then `audit_ui.py --strict` over a
    **new** module's stylesheets — never a delivered deck
11. `scripts/check_slide_text.py <course>` — what the pages SAY (L22); then
    `scripts/check_script_match.py <course> --module <n>` — the words are exactly the approved script (L29)
12. `scripts/check_plain_language.py <course>` — your own report, last before sending it (L25)
13. `retrofit/scripts/detect_expert_edits.py <module> --record --version <v>` — **last of all**, after everything else passes (L24)
14. **In retrofit only** — `retrofit/scripts/check_language.py <course> --declare <LANG>`, and
    `retrofit/scripts/classify_module.py` **again**

Then write `templates/factory-notes.md` into the course folder: what was produced, every marker
with its source, the achieved ratio, what was moved to the handout and why, and a final section
of **feedback on this skill**. That last section is the only channel through which real use
reaches the skill — it is written by this skill during the run, never left for a human.
