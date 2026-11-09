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

**The acceptance test.** Someone who has never seen the course opens the instructor terminal, types their ID, picks the
module, presses **Start** and **Next** to the end — and a real accredited class is taught, in the programme's minutes,
with the trainees' tablets carrying every task the screens announce. This skill decides the mode, runs the gate and
routes; it writes no screens, tasks or content itself.

## Every reply to the operator — human, in three parts (L25)

The operator knows the sea and the course, nothing about computers. Every message, at every STOP, in their language:

| | English | Latviešu | Русский |
|---|---|---|---|
| what was done and what it means for the course | **Done** | **Izdarīts** | **Сделано** |
| what to open now, and exactly where (full path, what it opens in) | **Check now** | **Pārbaudiet tagad** | **Проверьте сейчас** |
| what happens next, and what the factory needs from them | **Next** | **Tālāk** | **Дальше** |

- **Everyday words** — no *script, JSON, commit, push, plugin, render, flag, schema, pipeline, build*; say what it is.
  A computer word that cannot be avoided gets its meaning beside it, once. Maritime terms stay fully professional (L28).
- **Short** — a few points, one idea each; numbers as the operator counts them; test results in one line.
- **A question is a choice with options** (one pop-up, L31). **A problem says** what is wrong, where (full path and
  the module / slide), how to see it, what to do, and how they will know it worked. **Offer**: *"tell me and I will"*.
- `knowledge/plain-language.json` → `every_reply` holds the rule; `scripts/check_plain_language.py` checks a report.

## The operator's request wins — L26

**The course material** (content, structure, emphasis, slides, examples, tasks, wording) is **done as asked** — never
refused, watered down or quietly ignored; their request in chat is the authorisation L18 asks for, and it reaches
expert-edited regions too (L24). Four hard limits stay: **the programme and its Main ILOs (L1, L2) · the official
hours (L1, L3) · no source, no maritime claim (L4) · the offline tablet (L6)**. A fact the operator states is a source:
use it, record it as theirs, list it in that module's script review. When a request hits a limit: one or two plain
sentences why, the closest option that works, and do that.

**The design** (colours, type, logo, shell, layouts, animation, recap, viewer, text size, space, the 3D share —
`knowledge/design-rules.json`) **is the person's to decide**:

1. Nothing conflicts → do it.
2. It goes against a factory rule → name the rule and the risk in one or two sentences (`design_choices.py rules`),
   ask **once**: *your way* / *the factory's way*.
3. Their way → do it fully and record it: `scripts/design_choices.py add <course> --rule <id> --choice "..." --said
   "<their words>" --risk "..."`. Every check then reports it as **their choice**; no build, fix or session changes it
   back, and it is never asked again.
4. The factory's way → keep the rule; their words go into `FEEDBACK_LOG.md`.

A check is never a reason to undo a person's wish. Every other "never" here governs the factory's own choices.

## Owner decisions in force — every law, one line

Where any older text in this factory disagrees with a row below, **the row wins**. Most rows are a check that stops the
build. Before bending, questioning or changing a law, or when a request seems to collide with one, read it in full:
L26 onwards in `references/owner-decisions.md` (grep `## L45`), every law with its reasons in `references/laws-in-full.md`.

| | The rule |
|---|---|
| **L1** | **The approved programme is law; minutes are its units.** An academic hour is what the programme says (never assume 60); each module's teaching time equals its allocated minutes exactly; what does not fit goes to the handout. `hours/scripts/check_hours.py` before believing any plan |
| **L2** | **Main ILOs copied verbatim** — never edited, renumbered or improved. Sub-ILOs may be re-expressed, `PROVISIONAL` until ratified, never renumbered where a trainee sees them. The programme governs; the IMO model course guides |
| **L3** | **Official hours never changed to fit a schedule**; no attendance, contact time or compliance record is ever made up |
| **L4** | **No source, no maritime claim.** Never fill a gap from memory; a stated gap is a good answer. Every claim proved in the course's knowledge base by the `fact-checker` before approval (`fact_check.py`) |
| **L5** | **Theory delivered as active learning** — aim for 80 % learner-active minutes (Track B, `data-active`); the programme's theory/practice split (Track A, `data-track`, `check_balance.py`) never changes; theory is never removed; never reach the target by renaming screens |
| **L6** | **Tablet-first, touch-first, offline** — targets ≥ 56 px, no hover-only control, nothing at class time needs a network |
| **L7** | **Nothing is useless until you have grepped** its id, class, label and filename across both terminals, the course and every generated script |
| **L8** | **Explain and relocate; do not delete** on a complaint. When the operator tells you to remove something, remove it (after L7) |
| **L9** | **Edit; do not regenerate** a stable artefact |
| **L10** | **Visible must be sufficient**: a line that refers to something names it on the same line; this outranks any word budget |
| **L11** | **A generated file is never hand-edited** — change its input or its generator and regenerate |
| **L12** | **Every asset has provenance, a licence and a look** (open every image); unclear rights are `RIGHTS_REVIEW_REQUIRED`: marked *rights not cleared*, the build carries on, publishing is refused |
| **L13** | **A visual explains** a mechanism, state change, relationship, flow, sequence or cause and effect — never decoration |
| **L14** | **Read only:** the reference course, `source_files`, the knowledge base and the Android app (the L40 hook refuses writes) |
| **L15** | **A green exit is not proof** — read the output and the line for what you changed; report failures as plainly as passes |
| **L16** | **The factory builds and reports; the owner approves, commits, publishes and installs** |
| **L17** | **Every screen looks composed** — a big empty box or a huddle in a corner is a defect, however green the checks |
| **L18** | **Content is locked, delivery is free** (`retrofit/knowledge/content-lock.json`): meaning, ILOs, hours, assessment intent, exercises, terms, facts and language need authorisation; screens, layout, visuals, animation, interaction and code are rebuilt freely. An old visual is a teaching decision: keep the decision, rebuild the implementation |
| **L19** | **Every course is in English**, never asked; the programme stays in its own language and is quoted in English; chat and notes follow the operator. `retrofit/scripts/check_language.py` |
| **L20** | **A figure that claims to move is proved alive** (moves or responds; static is a defect for a dynamic idea) by a probe that can see |
| **L21** | **The Android app is a publish target, not a workspace** — read only until a person approves that course and version in their own words: *"Approved. Publish this course to the NOVIKONTAS training app."* (`publish.py --approved-by`) |
| **L22** | **A slide is not an internal document** — no file talk, sources or review notes on what a trainee reads (`check_slide_text.py`) |
| **L23** | **A topic screen leads with what shows it** — the visual above the prose, looked for before the words are set |
| **L24** | **An expert's change is content** (`retrofit/scripts/detect_expert_edits.py`, evidence or ask): restyled, never rewritten by the factory; the operator may still change it |
| **L25** | **The reader does not work in IT** — see *Every reply to the operator* |
| **L26** | **The operator's request wins** — see above |
| **L27** | Three test levels, all on the **trainee tablet**: a self-check shows the trainee's own score; the **module check** shows the score - no pass mark and no PASSED / NOT PASSED; the **final assessment** is the only one with the pass mark (70 %) and is blind |
| **L28** | **Course type** `NEW_ENTRANT` / `EXPERIENCED` from intake shapes the build; never easier names — the professional terms, explained; every model-course instrument and simulator is assumed available |
| **L29** | **A word-for-word content script** per module is approved before any HTML; the slides say exactly that (`check_script_match.py`) |
| **L30** | **Module 1 is a pilot**, approved before any other module is built |
| **L31** | **Ask like a colleague** — questions batched into one pop-up with options at the next STOP; honesty markers in `factory-notes.md`, never on a slide |
| **L32** | **The course remembers** — see below |
| **L33** | **Pictures: found before made** — knowledge base → old course → source files → internet → generated; small ones enlarged; nobody is asked to take a photo; nothing a trainee must recognise is invented |
| **L34** | **One module per programme topic**, in its order, with its hours; never merged or split; the final assessment is the last module |
| **L35** | **Two tablets** — slides on the instructor's, tasks only on the trainee's, opened with **OPEN TASK** |
| **L36** | **Enough theory before any task** (`knowledge/theory-rules.json`, `content_script.py`) |
| **L37** | **Every slide names its picture** — kind, what it shows, who makes it (`knowledge/media-and-tasks.json`) |
| **L38** | **Tasks varied and hands-on, no typing**; a self-check has at most 2 basic tasks (choose, match, order), the rest rich (3D, animation, a panel) — 3 + 2 in a set of five (`content_script.py` `t_sc_mix`) |
| **L39** | **A colleague gets only the HTML**; the real-tablet test is the owner's, at the end |
| **L40** | **The factory works in `course\`**; the master folder's source files, knowledge base and old course are read only (`hooks/guard_writes.py` refuses a write) |
| **L41** | **The old course is the foundation** — read whole at intake (`scripts/old_course.py`); each module says what it keeps, modernises and adds |
| **L42** | **Tasks usable with zero tablet experience** — tap and drag, big controls, instant feedback (`course-task-ux` §0) |
| **L43** | **Every module in its own folder**, complete and offline (`scripts/check_module_folder.py`) |
| **L44** | **Three places in `course\`**: `to_review\`, `modules\`, `working_claude\` (`workspace.py tidy`) |
| **L45** | **The classroom system's own rules** (`knowledge/classroom-system.json`, `check_course_package.py`) |
| **L46** | **3D at full quality and smooth on the tablet**; its share is L67's |
| **L47** | **A generated picture only within the budget the operator said yes to** — one yes per course at Stage 2 (`intake.json` `picture_budget`) |
| **L48** | **Bloom measured, and lifted by the tablet** — one level a course toward the outcome (`bloom/GUIDE.md`, `bloom_map.py`) |
| **L49** | **20 / 80 in class, every theory slide kept** — theory-as-activity proposed per sub-topic at Stage 2 (`active/GUIDE.md`) |
| **L50** | **A fix is not a build** — find every place, one list, one yes, change, one check (`fix/GUIDE.md`, `fix.py`) |
| **L51** | **Every picture opens full screen; every module closes with the same recap** before its module check |
| **L52** | **As many real photographs as possible**; a source-book figure only once a named person cleared it (`check_assets.py clear`) |
| **L53** | **No empty space, good padding** — decks pass the layout audits before they are shown |
| **L54** | **Every drawing whole and clean** (`audit_drawing.js`) |
| **L55** | **Diagrams come from the figure kit** (`course-visuals/kit/SPEC.md`), never a one-off SVG; a missing part is made into the kit |
| **L56** | **A photograph carries what it shows and its credit into the full-screen view** — no credit on the slide |
| **L57** | **A drawing of real things carries their real photographs**, unasked |
| **L58** | **Every photograph once in the whole course** |
| **L59** | **No module before its map** — ILO map approved and the knowledge-base decision recorded (`course_gate.py`) |
| **L60** | **A 3D scene in every module whose subject allows** — declined only with the operator's reason |
| **L61** | **Every slide is one of the layout templates** (`course-module-ui/knowledge/layout-templates.json`), chosen by the compiler; a picture beside words gets the box its names need (40-65 %, `layout_fit.py`) or is made another kind - never squeezed |
| **L62** | **Never the same look three times in a row (two is a note for the reviewer); at least 80 % of slides on the light ground** — the compiler does it |
| **L63** | **Equipment drawn as it looks on board** (`course-visuals/kit/PARTS.md`) |
| **L64** | **A module in 30-40 min, its fixes in 20** — the pre-check first (`precheck.py`); a rebuild is a fix (`fix.py rebuild`) |
| **L65** | **A drawing that moves stays smooth** (`audit_motion.js`) |
| **L66** | **Every item a simulator can train is trained on one** (`coverage/SIMULATORS.md`, `sim_coverage.py check`) |
| **L67** | **A slide's picture is 3D or a photograph, never a flat line drawing; every slide moves on Next** — 60-80 % of a module's teaching slides are interactive 3D, the rest a static 3D render or a photograph (`content_script.py` and `check_course_package.py` stop outside it; `gb_upgrade.css`, `gb_steps.js`) |
| **L68** | **The Instructor-Led Course Development Guideline** — active means every trainee commits to an output; a passive run at most 15 min and 20 % of theory, or a one-line reason (`instructor-led/GUIDE.md`, `instructor_led.py check`) |
| **L69** | **The experts get the pedagogy first** — Bloom now, Bloom proposed and the activities, before any script (`pedagogy_review.py`, `bloom/GUIDE.md` §5) |
| **L70** | **Built after the expert's Ready** — the office PC builds unattended; see *Auto build* |
| **L71** | **Kept, lifted one level, seen whole** — the old course's order and theory kept; every claim proved; the build walks every Next (`fit_gate.py`); a module with no PASS is not done |

## The course remembers — L32

`scripts/course_memory.py`; templates `templates/COURSE_STATE.md`, `FEEDBACK_LOG.md`, `COURSE_PATTERN.md`; kept in
`course\working_claude\`, never shipped.

- **Every session starts by reading `COURSE_STATE.md`** (a new course: `course_memory.py start`), then `STANDARDS.md`
  and the last rows of `FEEDBACK_LOG.md` and `design_choices.py list` — never re-ask or re-decide what they hold.
- **At every STOP** update it (stage, approvals, open questions, next step, file map); `course_memory.py check` says
  whether a new session could resume from it.
- **Every correction** goes into `FEEDBACK_LOG.md` at once, in the operator's words; a stated fact is *operator-stated*.
- **When the operator is happy**, offer a pattern file: `draft-pattern`, **show it to the operator in plain language**,
  let them change any point, then `approve-pattern --by "<name>"`. Approved patterns (`patterns --course-type <type>`)
  are guidance for later courses, never rules.

## Mode first, then read one lane

| Mode | You are asked to | Read |
|---|---|---|
| **plan** | turn an accredited programme into modules with hours that add up | `hours/GUIDE.md` |
| **retrofit** | upgrade, redesign or "make presentable" material that **already exists** | `retrofit/GUIDE.md` |
| **preview** | let a colleague see the course | `course-tablet-publisher` → `references/preview-and-approval.md` |
| **edit** | make the content or structure change the operator named — **do it** (L26) | `retrofit/knowledge/routing.json` § edit_triggers; once built, check it as a fix |
| **fix** | correct **built** modules — one, some or all; also a rebuild of one (`fix.py rebuild`) (L50) | `fix/GUIDE.md` and nothing else |
| **restyle** | one **narrow** cosmetic change and nothing else | `retrofit/knowledge/routing.json` § restyle |
| **ship** | put a built course into the training app | `scripts/course_portal.py upload` - a draft release in the staging editor, which the office publishes (L70); `tablet/GUIDE.md` |
| **audit** | check a course against the programme and the terminals | `coverage/GUIDE.md`, then the lanes' verify sections |
| **orchestrate** | build a WHOLE course, one agent per module | `orchestration/GUIDE.md` |

`retrofit/knowledge/routing.json` decides the mode from the operator's intent, never a phrase. A restyle needs a narrow
target *and* a limiter ("only the colours"); give exactly that and say in one line what a retrofit would add. Never load
a lane the mode does not need (a retrofit reads `hours/` for Track A only). Why each lane exists:
`references/routing-notes.md`.

**Outside this bundle — point, never copy:** screen craft and measurement `course-module-ux` · the look
`course-module-ui` · what visual teaches a concept, assets and rights `course-visuals` · task screens `course-task-ux` ·
publishing `course-tablet-publisher` · intake, course plan, `COURSE_START.json`, ILO wording, exercises, handouts, tests,
pptx and the brand: the `novikontas-*` skills · source PDFs: the knowledge base, read only through
`kb/scripts/kb_tool.py`. An organisation skill that is not installed: its fallback in `org/ORG_DEPENDENCIES.md` (three
are blocking: pedagogy-toolkit, handouts, course-start), the route recorded in `factory-notes.md` §0; never paraphrase
an absent skill from memory.

## The brief — a call and a folder (Stage 1, intake)

The operator calls the factory and gives a folder; nothing else is required, and nothing derivable is asked back (no
skill names, module split, screen count, task codes, pass marks, layout or lane). **Look in the folder before asking.**
`knowledge/intake.json` is the authority. In order:

0. **The folder is the master folder** (L40): `python scripts/workspace.py <folder>` names `course\` beside it.
1. **Find** the programme, the IMO model course, the knowledge base and the old course; propose the course type.
   **Read the old course whole** (`old_course.py inventory` and `images`). **No knowledge base?** `kb_tool.py find
   <folder>` — suggest one unasked, in plain words, its question in the pop-up. **A shared subject library?**
   `course-visuals/scripts/subject_library.py covers "<title, STCW ref>"` — used before the knowledge base and the
   internet; findings go back with `contribute`; a new course is registered once its modules folder exists.
2. **Sort the sources** — `kb_tool.py sources <kb> --course <course>` (`kb/GUIDE.md`); several editions → one question.
3. **Ask what is missing, once**, in one pop-up of up to four questions: the programme (the one blocking answer), the
   knowledge base, the old course, the course type (the programme's pointer *Recommended*), editions, and in retrofit
   only when `detect_expert_edits.py` says `nothing-to-go-on`, whether anyone edited it by hand (L24).
4. **Record** in `working_claude\intake.json`; editions with `kb_tool.py decide`, the knowledge base with `kb_tool.py
   decision`. Never web-search during intake; `UNKNOWN` means asked and not known.

Corrections arrive in the operator's words ("too much text on screen 4"): act on them, never turn one into an interview.

## The gate — Stage 2, approved before anything is built

1. **Experts first (L69).** Bloom now, Bloom proposed and the activities, per topic, in `to_review\pedagogy\` (Word,
   HTML, PDF): judge each topic in `pedagogy_review.json` by `bloom/GUIDE.md` §5, `pedagogy_review.py check` and
   `render`; the experts answer in the training app's editor (`course_portal.py create`, `push --pedagogy`, `pull`).
2. **Simulators (L66), unasked.** `coverage/scripts/sim_coverage.py needed <course>`; where needed, the maps and GAP
   drafts from `coverage/SIMULATORS.md`, and `sim_coverage.py check` passes before "next".
3. **One page:** `python scripts/make_architecture_page.py --course <course> --check`, then without `--check`. It
   shows: modules one per topic with minutes and the total against the programme (L1, L34) · the two tablets (L35) ·
   Main ILOs verbatim, with `text_en` when the programme is not English (L2, L19) · Sub-ILOs kept / re-expressed /
   added with reasons · per module the activities, tasks, equipment, self-checks and module check (L5, L27, L28, L36) ·
   the final with its pass mark · theory as activity with **Keep / Strike** per proposal, all decided before "next"
   (`active_plan.py decide`, L49) · Bloom levels (L48) · the ILO map (`working_claude\ilo_map.json`) · the
   knowledge-base decision. Headings in the operator's language (`operator_language`).
4. **In the same pop-up as "next":** how the modules are built — *all at once with agents* (Recommended for 4 or more;
   `orchestration/workflows/build_course.js`) or *module by module in this session* — and the picture budget ("about
   N pictures, about €X. Yes?"). Record `build_mode` and `picture_budget` in `intake.json` and COURSE_STATE; never ask
   again. `"workflow"` is the operator's own request for agents: run the workflow once the scripts are approved.
5. **Record "next":** `make_architecture_page.py --course <course> --approve --by "<name>"` — refused while the
   knowledge-base decision is missing, a module has nothing in the map, or a proposal waits. A later Sub-ILO change
   stops new modules until it is approved again. **No module before the map (L59):** `content_script.py` and
   `compile_module.py --init-build` exit 2, and `course_gate.py <course>` says what is missing.

## Stage 3 — the content script, approved before any HTML (L29)

`script/GUIDE.md` is the lane, `scripts/content_script.py` does it. Per module, in teaching order: **part 1, the
instructor tablet** — each slide's exact words, picture slot, minutes, notes, and a task slide with OPEN TASK where a
task begins; **part 2, the trainee tablet** — each task, one question a screen, answers, feedback, the trainee's own
score. Begin from the module's ILO map rows (`ilo_map.py show`), the old course's keep / modernise / add and the
knowledge base (`kb_tool.py search`). Before scripts are written in parallel, `STANDARDS.md` gets the course's
`## Ship profile`.

- **Taught before asked (L36, L71):** one `task-coverage-checker` agent per module, before the `fact-checker`, judges
  every question against the slides before it (`task_cover.py`); approval is refused while one is unjudged, partly or
  not covered.
- **Proved (L4):** one `fact-checker` agent per module; approval is refused while a claim is unjudged or unproved.
- **Checked:** the theory, slide-text, pictures-and-tasks and ILO-map checks head the review page; a must-fix blocks
  approval (`--despite-findings` only on the operator's word). Questions carry `"sub_ilo"`, and `"bloom"` + `"bloom_why"`
  when written above their task type's level.
- **Reviewed as a page and a Word file:** the operator corrects by typing, by Word comment or in the chat; the
  operator-stated facts are listed once. The **Bloom card** (L48) shows each question's level and the share at *Apply*
  or higher (suggested 50 %) — suggestions only.
- **Shown before applied:** `read` / `propose` print what was understood; `apply --confirmed` only after the operator's yes. A written script changes only this way, never by editing `MNN.json` (a builder's trim included): a hand edit is missing from `FEEDBACK_LOG.md` and drops the approval.
- **Approved by the operator's own act:** `approve --by <name>` in their session; an unattended run builds `--draft`;
  never approve on an instruction relayed from another session. The one exception is the expert's Ready (L70).
- **Built, never typed:** the deck and task pages by `compile/scripts/compile_module.py`, the course's own pages and
  additional materials by `compile_course.py`. **One command builds and checks a module:** `compile/scripts/build_module.py
  <course> --module N` — start at the Quickstart of `compile/GUIDE.md`; figure specs from `course-visuals/kit/CATALOGUE.md`.

## Building

`knowledge/build-order.json` is the authority (programme → syllabus → knowledge base → ILO map → modules → **gate** →
screen inventory → visual system → visual plan → tasks → screens → handout → assessment → module plans → terminals →
verify). Not negotiable: the screen inventory and the visual system before any screen; task pages before the deck
announces them (`tablet/` cross-check).

- **Two phases (2.73.0):** Phase A with no agent — placeholders of each picture slot's shape and every check that does
  not need the pictures (`compile/scripts/phase_a.py`); Phase B fills the pictures from `MNN_VISUAL_NEEDS.md` and the
  photo catalogue. A placeholder never ships.
- **The look is routed:** `course-module-ui` (`design_system.py install`, `references/vocabulary.md`); to choose and fill
  a screen read one file, `course-module-ui/knowledge/blueprints.json`. GAS BASIC Module 1 is the visual reference,
  not a template: no fixed slide count, and low density is not low depth.
- **Done means PASS:** a module is built only when `build_module.py` printed PASS; the workflow blocks a module without
  one, and `course_portal.py upload` refuses while a module's last build failed.
- **Which model each helper agent gets** — the same in `build_course.js` (`MECHANICAL` / `JUDGEMENT`) and in a session
  that hands out the agents itself (the Auto build, the factory trial):

  | Job | Model |
  |---|---|
  | Build loop (`build_module.py` until PASS, a carry-on), Phase A, photo search, figure shots, gate, assembly | `sonnet` |
  | 3D scenes and their review, figure review and figure fixes, the screenshot review, QA, the fixes QA's findings ask for | `opus`, high effort |
  | Reader, script writer | the session's own |

## Auto build — after the expert's Ready (L70)

A run from `course_portal.py watch --once` (`NOVIKONTAS_AUTO_BUILD=1`) has nobody to answer:

- Carry out every expert note (`pedagogy_review.py check`) and write its `done`. Pass every STOP with the expert's name:
  `--approve --by "<expert> (Ready in editor)"`, `content_script.py approve ... --by "<expert> (Ready in editor)"`; the
  build plan question takes its first option.
- Never ask: a question goes to `working_claude/OPEN_EXPERT_QUESTIONS.md` with the choice made, and the build goes on.
- Each script, before approval: the `task-coverage-checker`, then the `fact-checker`, each ending `fixes --apply`; a
  question listed for the person goes to `OPEN_EXPERT_QUESTIONS.md`.
- No paid pictures. Free sources first — Wikimedia Commons, DVIDS, USCG, NOAA, the old course, the knowledge base (the
  `visual-sourcer`; small ones enlarged) — then Nano Banana in the Gemini app if a signed-in browser is there
  (`gemini-browser`). `picture_briefs.py queue` / `place`. An unfilled space keeps its brief and does not stop the build.
- Build every module, compile COURSE.html, run the checks, fix what they find, then each module's one polish round
  (`compile/GUIDE.md` step 6) - each helper agent on its model in *Building* (a Sonnet builder per module, its judges,
  fixers and polish on Opus). Never push to git; never write outside the course folder.
- End with one line: `AUTO BUILD DONE`, `AUTO BUILD DONE - PICTURES PENDING: <n>` or `AUTO BUILD STOPPED: <why>`.

**After an attended session** the course goes up unasked: `course_portal.py upload --course <course>` is the last step
of a build and of `fix.py rebuild`; it imports a draft once nothing but picture spaces stops it, else says what does.

## Honesty markers

`novikontas-course-start` owns the definitions: `UNKNOWN` asked and not known · `PLACEHOLDER` structure right, content missing · `PROVISIONAL` depends on something
unapproved (every re-expressed Sub-ILO, every unratified pass mark) · `[VERIFY: <what>]` asserted from a source not
confirmed. Never invent regulatory content, hours, pass marks or citations; every marker used is listed in
`factory-notes.md`.

## Verify before reporting done

After a change to the factory itself, `scripts/factory_trial.py run` builds the trial modules from scratch and scores
them against the last trial. The list below is the sign-off of a build, a retrofit and the handover — a fix runs only
the one check for its kind of change (`fix/GUIDE.md` §4). Read every output (L15); why each check exists:
`references/verify-in-full.md`.

1. `hours/scripts/check_hours.py` — minutes match the programme
2. `coverage/scripts/check_syllabus_coverage.py` — every itemised model-course outcome is taught
3. `tablet/scripts/verify_course.py`, `verify_links.py` (merged asset root), `audit_navigation.py`, `crosscheck_tasks.py`
4. `course-module-ux`'s measurement lane for the screens
5. `course-visuals/scripts/check_visuals.py`, `check_assets.py`; in the page `GBVerifyFigures.run()` and `await
   GBVerifyFigures.motion()` (L20); `course-visuals/review/GUIDE.md`; nothing at `RIGHTS_REVIEW_REQUIRED` ships
6. `course-visuals/scripts/check_visual_first.py <module> --strict` (L23), then `write_visual_handoff.py <module>`
7. `course-module-ui/scripts/design_system.py check <module>`; `audit_ui.py --strict` over a **new** module's stylesheets
8. `scripts/check_slide_text.py <course>` (L22), then `check_script_match.py <course> --module <n>` (L29)
9. `instructor-led`: `scripts/instructor_led.py check` (L68); `coverage/scripts/sim_coverage.py check` (L66)
10. `scripts/check_plain_language.py <course>` — your own report, last before sending it (L25)
11. `retrofit/scripts/detect_expert_edits.py <module> --record --version <v>` — last of all (L24)
12. In retrofit only — `retrofit/scripts/check_language.py <course> --declare <LANG>` and `classify_module.py` again

Then write `templates/factory-notes.md` into the course folder: what was made, every marker with its source, the
achieved ratio, what moved to the handout and why, and a last section of **feedback on this skill** — written during
the run, never left for a human.
