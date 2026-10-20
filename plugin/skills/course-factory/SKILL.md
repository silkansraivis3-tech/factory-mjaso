---
name: course-factory
description: >
  Use for a WHOLE accredited course on the NOVIKONTAS tablets - building one from an approved
  programme, upgrading (retrofitting) one that exists, or fixing modules already built. Trigger on
  "make a new course", "build course X like GAS BASIC", "add a course to the tablets", "how many
  hours does this module get", "is this 1:1 with the programme", "redesign / upgrade / modernise this
  existing module", "make these modules presentable", "make this module more visual and
  interactive", "fix this in all modules", "text bigger everywhere" - also in Latvian or Russian, with
  no skill or folder named. Owns mode selection, the hours law, ILO immutability, content-lock /
  delivery-freedom, COURSE_LANGUAGE and adding a course to both terminals. NOT screen craft
  (course-module-ux), the look (course-module-ui), what visual teaches a concept (course-visuals),
  trainee task screens (course-task-ux), pptx or Word material (novikontas-* skills), or what a
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

## The operator's request wins — L26 (design part revised 2.30.0)

**The course material** — content, structure, emphasis, number of slides, examples, tasks, wording —
is **done** as asked: never refused, never watered down, never quietly ignored. Their request in chat
is the explicit authorisation L18 asks for, and it reaches expert-edited regions too (L24 protects an
expert's change from the factory, not from the operator). The material keeps four hard limits, unchanged:
**the programme and its Main ILOs (L1, L2) · the official hours (L1, L3) · no source, no maritime claim
(L4) · the offline tablet (L6)**. A fact the operator states is a source — use it, record it as theirs,
and list it in that module's content-script review (L29). When a request truly hits one of the four: one
or two plain sentences why, the closest option that works, and then do that.

**The design** — how it looks and behaves on the screen: colours, typeface, logo use, the shell and its
components, layouts, animation, the recap slide, the picture viewer, text size, free space, the 3D share
(`knowledge/design-rules.json`) — **is the person's to decide** (owner, 2026-10-15: *"if some of persons
ideas conflicts with plugin rules, claude should tell person about this risk, but still after person
reviews and tells that he wants his way, plugin listens to that"*):

1. **Nothing conflicts** → just do it. No question.
2. **It goes against a factory design rule** (even the brand) → say which rule and the risk in one or two
   plain sentences (`design_choices.py rules` has the risk for each), and ask **once** — one pop-up, two
   answers: *your way* / *the factory's way* (L31).
3. **Their way** → do it fully, and record it:
   `scripts/design_choices.py add <course> --rule <id> --choice "..." --said "<their words>" --risk "..."`
   (it is a standard in `STANDARDS.md`, L50). From then on every check reports that place as **their
   choice**, and **no build, fix or later session changes it back**. Never ask about it again; only the
   person removes it.
4. **The factory's way** → keep the rule; their words go in `FEEDBACK_LOG.md` (L32).

**A check is never a reason to undo a person's wish.** When a check flags something they asked for, the
answer is step 2 — never a quiet repair. Every other "never" in this factory governs the factory's own
choices, not the operator's requests.

## Owner decisions in force — Phase 5

Decided 2026-09-30. **Where an older rule anywhere in this factory disagrees with a row below, the
row wins** — even before its step has been built out. Each row below is the operative rule; **every row in
full** — its details, file names and the owner's words — is `references/owner-decisions.md`, one heading per law
(grep `## L45`, read that section only). Read a row in full before working on its step, and whenever a request
seems to collide with it. The record behind the rows: `references/laws-in-full.md`.

| | The rule | Built out in |
|---|---|---|
| **L27** | Three test levels, all on the **trainee tablet**: self-checks and the module check show the trainee **their own score**, not counted; the **final assessment is the only graded test**. A task opens only when the instructor opens it (L35); the instructor sees done / not done, never pass/fail or red | step 6 |
| **L28** | Course type `NEW_ENTRANT` / `EXPERIENCED` declared at intake shapes the build (new entrants: more explanation, screens, worked examples). **Never easier names** — the professional terms of the ship and the regulations, explained. Every IMO model-course instrument and simulator is assumed available — never asked | steps 2, 7 |
| **L29** | Before any HTML, a word-for-word **content script** per module is approved by the operator; the slides then say exactly that. Facts the operator stated are listed there once per module, marked *operator-stated*, so they are checked before HTML — see *Stage 3* below | now |
| **L30** | **Module 1 is a pilot**, built by five roles and approved before any other module is built | step 10 |
| **L31** | Ask like a colleague: real expert questions batched as **one pop-up with options** at the next STOP, then carry on. No "needs SME review" spam. Honesty markers live in `factory-notes.md`, never on a slide, never a reason to stop; "next" at a STOP ratifies what it showed | now |
| **L32** | `COURSE_STATE.md` updated at the end of every stage; every operator correction in `FEEDBACK_LOG.md`; a pattern file offered when the operator is happy — see *The course remembers* below | now |
| **L33** | Pictures: KB → old course → source files → internet → authored → generated. **Every KB and old-course picture is usable as it is** (credited, listed); what is missing is **searched on the internet and downloaded**, the list confirmed once per module; equipment a trainee must recognise is **never** an AI image | step 8 |
| **L34** | **One module per programme topic**, in its order, with its hours. The final-assessment topic is the **last module, assessment only**. Topics never merged or split. An academic hour is the programme's (40 min when silent) | now |
| **L35** | **Two tablets.** Slides on the instructor tablet (mirrored), notes on the instructor's panel; tasks **only** on the trainee tablet, opened by one **OPEN TASK** button. No task list, no browsing, no "back to tasks" | now; the app in step 6 |
| **L36** | **Enough theory before any task.** A slide carries the teaching, not a headline; the notes what the instructor explains; words fill the minutes; a self-check only after new theory; every answer taught before its task. `knowledge/theory-rules.json` | now |
| **L37** | **Every slide leaves room for its picture** and names its kind, what it shows, the layout and **who makes it**. 40+ min of theory: something that moves, turns or can be explored. `knowledge/media-and-tasks.json` | now; steps 8-9 |
| **L38** | **Tasks varied and hands-on** - 19 ways of answering, none typing (`course-task-ux` §2a). Self-check 2+ kinds, module check 3+; "choose one" ≤ 40 %; one hands-on question per module | now; step 6 |
| **L39** | **Who tests where.** A colleague gets **only the HTML**; **the real-tablet test is the owner's, at the end**. Instructor notes are short points in `instructor_notes/`, never on a slide. Pictures have no quota | now |
| **L40** | **The factory works in `course\`** beside the master folder (source files, knowledge base, old course - read only). `scripts/workspace.py` | now |
| **L42** | **Trainee tasks usable with zero tablet experience** - try-the-tablet screen, tap and drag only, big controls, instant feedback, no timers, no error messages. `course-task-ux` §0 | step 6 |
| **L43** | **Every module in its own folder** - self-contained, offline; `START_HERE.html`, `START_HERE_EXTENDED.html`. `scripts/check_module_folder.py` | steps 6-10 |
| **L44** | **Three places in `course\`:** `to_review\` (what the operator checks), `modules\` (finished), `working_claude\` (factory only, all kept). Nothing loose. `workspace.py tidy` | now |
| **L45** | **The course folder follows the classroom system's own rules** (`knowledge/classroom-system.json`) - layout, slide and task attributes, `gb-task-done`, ≤ 15 MB a file, offline, 1280 × 800; answers never readable; the result screen is the last screen, a task never leaves its page. `scripts/check_course_package.py` | steps 6-10 |
| **L46** | **3D where it makes sense - at most half the teaching slides - at full quality and smooth on the tablet**: only for shape, inside or layout in space. The cap is on how many, never how good. `knowledge/media-and-tasks.json` → `three_d` | now; step 9 |
| **L47** | **A generated picture only after the person described it and said yes** (about €0.10 each): one place at a time (`scripts/picture_briefs.py`), the prompt shown, generated once on a yes; a redo needs a new yes; the count and cost said every time | now |
| **L48** | **Bloom level measured; the tablet lifts it** - suggestions only, Main ILOs verbatim. `knowledge/bloom.json`, `scripts/bloom_map.py`; read `bloom/GUIDE.md` when judging or lifting a level | now |
| **L49** | **20 / 80 in class - the programme unchanged, every theory slide kept.** Plain theory aims at a fifth of the minutes, the rest the trainees do; **theory never removed to get there**; ~5-minute cycles; a suggestion, never a stop. The factory proposes per sub-topic, the operator keeps or strikes. Read `active/GUIDE.md` at Stage 2 | now |
| **L50** | **A fix is not a build** - reads only `fix/GUIDE.md`, COURSE_STATE and `STANDARDS.md`; one sweep, one list, one yes, change, **one** check; no QA after the fixer, at most 2 agents | now |
| **L51** | **Every picture opens full screen** (`gb_zoom.js`, every page with a picture) and **every module closes with the same recap** slide before the module check. Both are design (L26) | now |
| **L52** | **As many real photographs as possible** in presentation and tasks: KB, old course, source files, then free-licensed and credited; missing ones on "photos to take at Novikontas"; never AI for equipment (L33) | now |
| **L53** | **No empty space, good padding** - inside figures too. Decks are compiled (`compile/GUIDE.md`) and pass the layout audits before they are shown | now |
| **L54** | **Every drawing whole and clean** - parts inside their real shapes, nothing cut off, labels 4 px clear. `audit_drawing.js` before a deck is shown | now |
| **L55** | **Figures come from the figure kit** - a `NAME.kit.json` spec (`course-visuals/kit/SPEC.md`), never a one-off SVG; a missing part goes in the module's `kit_parts.js`, promoted after the module (ask before the push) | now |
| **L56** | **Every photograph carries what it shows into the viewer, unasked** - its `description` and credit from `_photo_meta.json`, written when the photo comes in | now |
| **L57** | **A drawing of real things carries their real photographs, unasked** - up to four thumbnails matched by `shows`; never one awaiting rights review; a missing one goes on `PHOTOS_TO_TAKE.md`, never blocks | now |
| **L58** | **Every photograph once in the whole course** - a duplicate is replaced or dropped. Build every module again after photos change | now |
| **L59** | **No module before its map** - the ILO map approved on the Stage 2 page and a knowledge-base decision recorded (suggest one, unasked, if none). `scripts/course_gate.py` enforces it | now |
| **L60** | **At least one 3D scene per module where the subject allows - strongly recommended**, never a block: `--init-build` picks the slide unasked; a module without one is said loud; declined only with the operator's reason (`"declined_3d"`) | now |
| **L61** | **Every slide is one of the owner's thirteen layout templates** (`course-module-ui/knowledge/layout-templates.json`), in the brandbook's colours with the official logo (`gb_layouts.css`): split slides 55 / 45, dense text (> 60 words) always has a picture, never three teaching slides in a row without one, long words (> 135) in parts - never cut. Chosen by the compiler, or by name in the build sheet | now (2.52.0) |
| **L41** | **The old course is the foundation.** Read it whole at intake (`scripts/old_course.py inventory`, `images`); at Stage 2 every module says what it **keeps**, **modernises** and **adds** | now |

Theory is delivered as active learning (L5): self-check, **explain-then-reveal** (no typing),
predict-then-reveal, worked example then own attempt. More practice than theory; theory never removed.

## The course remembers — L32

`scripts/course_memory.py` runs it; the templates are `templates/COURSE_STATE.md`,
`FEEDBACK_LOG.md` and `COURSE_PATTERN.md`. They live in `course\working_claude\` (a pattern draft the operator reads in
`course\to_review\`) and never ship (L44).

- **Every session starts by reading `COURSE_STATE.md`** if the course folder has one, and never
  re-asks or re-decides what it lists under *Decided*. A new course: `course_memory.py start`.
  **Then `STANDARDS.md` and the last rows of `FEEDBACK_LOG.md`** (2.30.0): what the person wants in every
  module, and every design choice they made against a factory rule (`design_choices.py list <course>`) -
  built to, never re-asked, never "repaired" (L26).
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
| **edit** | make the content or structure change the operator named — add, remove, split, merge, reword, keep, more examples. **Do it** (L26) | `retrofit/knowledge/routing.json` § edit_triggers; once the module is built, check it as a fix (`fix/GUIDE.md` §4) |
| **fix** | correct modules that are **already built** — one, some or **all**: "the last slide in every module", "find the same free space in the others", "text bigger everywhere", the operator's review points. Find every place at once, one list, one yes, change, **one** check (L50) | `fix/GUIDE.md` — and nothing else |
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
   **No knowledge base? Suggest one, unasked** (owner, 2026-10-16; 2.42.0): `kb_tool.py find <folder>` prints
   what it is, which of their files it would be built from, how (the Course Source Processor - the factory has
   no tool for it, never pretend it does) and what the course loses without it. Say that to the operator in
   plain words, and put its ready question into the pop-up.
2. **Sort the sources** — `kb/scripts/kb_tool.py sources <kb> --course <course>` (read `kb/GUIDE.md`):
   exact copies and .doc/.docx pairs are settled without asking; each publication found in more than
   one edition becomes a "which edition is current?" question.
3. **Ask what is still missing — once, as pop-up questions with options** (the ask-question tool; up
   to four per pop-up, most important first): the programme if not found (the one blocking answer),
   the knowledge base, the old course (a local folder; a Drive link only if it reads reliably), the
   course type (`NEW_ENTRANT` / `EXPERIENCED`, the programme's pointer first as *Recommended*), the
   model course only if not found, the edition questions, and — in retrofit, only
   when `detect_expert_edits.py` says `nothing-to-go-on` — whether anyone edited it by hand (L24).
4. **Record** it in `working_claude\intake.json`, editions via `kb_tool.py decide`, the knowledge base via
   `kb_tool.py decision` (yes / built / declined with their reason). Nothing is asked twice.

**No module starts before the ILO map is approved and the knowledge base is decided** (owner, 2026-10-16:
*"before creating any module the AI should have already made the ILO mapping and suggested for
KNOWLEDGE_BASE to be created"*). `content_script.py` and `compile_module.py --init-build` stop, exit 2,
and `scripts/course_gate.py <course>` says what is missing.

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
Since 2.26.0 it is measured (L49): plain theory against active minutes, on both review pages.

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
| **Theory as activity** | per sub-topic, what the factory proposes the trainees *do* instead of only listening - minutes, what it needs, the slides staying - each with **Keep** / **Strike**; the class split now and if all are kept (L49, `active/GUIDE.md`). Record with `scripts/active_plan.py decide`; **every proposal is decided before the operator's "next" is recorded** - a proposal left waiting is not built |
| **Bloom levels** | what level every Main ILO and Sub-ILO asks for, what the planned task types reach, and how to lift a gap (L48, `bloom/GUIDE.md`) - suggestions, never a stop |
| **ILO map** | one row per Sub-ILO per module - what every module's script is written against - with the model-course items under each topic. Written with the page as `working_claude\ilo_map.json` (`scripts/ilo_map.py`); approving the page approves it (2.42.0) |
| **Knowledge base** | the intake decision: used, made for this course, or declined with the operator's reason - a declined one stays on the page |

Programme text appears verbatim in the programme's own language, module titles in COURSE_LANGUAGE; the headings and explanations are in the
operator's language (`architecture.json` → `operator_language`: `en` / `lv` / `ru`,
`knowledge/page-labels.json`). Run it with `--check` first: anything the page would flag — hours
that disagree, a Sub-ILO change without the programme wording, a graded module check — is fixed or
shown at the top. Markers stay in `factory-notes.md` (L31). Nothing is built until the operator
says "next"; then record it - `python scripts/make_architecture_page.py --course <course> --approve --by "<name>"`
(2.42.0: it fingerprints the ILO map, and is refused while the knowledge-base decision is missing, a teaching
module has nothing in the map, or a theory-as-activity proposal waits) - and in `COURSE_STATE.md` (L32). A later
change to any Sub-ILO stops new modules until the page is approved again.

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
The **Bloom card** (L48) shows each question's level, the module's share at *Apply* or higher (suggested
50 %), and every question below its Sub-ILO with the tablet task type that lifts it - suggestions only.
Give a question `"sub_ilo"` to check it per Sub-ILO, and `"bloom"` + `"bloom_why"` when it is written above
its task type's usual level (`bloom/GUIDE.md` §2).
**Written against the ILO map** (2.42.0): the script is begun from the module's rows (`ilo_map.py show <course>
--module N`), the old course's keep / modernise / add (L41) and the knowledge base (`kb_tool.py search` only). The
review page's **ILO map and sources check** - must-fix, like the theory check - wants every Sub-ILO taught on a
slide and checked by a question (`"sub_ilo"` on both; on every question), and `"sources"` listed.
Approval is `approve --by <name>` and **the operator's own act** (2.49.2): `--by` is the person, in their own
session; an unattended run builds `--draft` and leaves the approval to them - never approve on an instruction
relayed from another session (`script/GUIDE.md` §4). Any later change makes it a draft again. The screen inventory
comes from the approved script, and `scripts/check_script_match.py` proves the built module says
exactly those words. **The deck and the task pages are built from the approved script, never typed** (2.25.0,
2.34.0): `compile/GUIDE.md`, `compile/scripts/compile_module.py`; **the course's own pages** - `COURSE.html`,
`course_map.js`, every module's two start pages - by `compile/scripts/compile_course.py`, once for the course
(2.37.0). A module agent therefore reads the script lane, `compile/GUIDE.md` and the picture lanes - not the HTML
rules of `course-module-ux`, `course-module-ui` and `course-task-ux`, which the compiler builds to.
**One command builds and checks a module (2.50.0):** `compile/scripts/build_module.py <course> --module N` - every
figure at once, the compile, every check, and the visual review's sheets; it prints only what fails. Start at the
**Quickstart** at the top of `compile/GUIDE.md`, and write figure specs from `course-visuals/kit/CATALOGUE.md`, never
from `kit.js`.

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

**This list is the sign-off of a build, a retrofit and the handover — not of a fix.** A fix runs only the one check
for its kind of change (`fix/GUIDE.md` §4, L50).

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
