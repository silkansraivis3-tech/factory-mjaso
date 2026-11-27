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

The operator knows the sea and the course, nothing about computers. Every message at a STOP, in their language, has
three parts: **Done** (what was done and what it means for the course) · **Check now** (what to open, the full path,
what it opens in) · **Next** (what happens next and what the factory needs from them).

- **Everyday words** — say what a thing is, not its computer name (*script, JSON, commit, plugin, render, build*); a
  computer word that cannot be avoided gets its meaning beside it, once. Maritime terms stay fully professional (L28).
- **Short** — a few points, one idea each; numbers as the operator counts them; test results in one line.
- **A question is a choice with options** (one pop-up, L31). **A problem says** what is wrong, where, how to see it,
  what to do, and how they will know it worked.
- `knowledge/plain-language.json` → `every_reply` holds the rule; `scripts/check_plain_language.py` checks a report.

## The operator's request wins — L26

**Course material** (content, structure, slides, tasks, wording) is done as asked, expert-edited regions too (L24); chat
is the authorisation L18 asks for. Four limits stay: **programme and Main ILOs (L1, L2) · official hours (L1, L3) · no
source, no maritime claim (L4) · the offline tablet (L6)**. A fact the operator states is a source: record it as theirs.
At a limit: one or two plain sentences why, then the closest option that works.

**Design** (colours, type, logo, layouts, animation, text size, space — `knowledge/design-rules.json`) is the person's.
If it breaks a factory rule, name the rule and risk once (`design_choices.py rules`) and ask *your way* / *the factory's
way*. Their way: do it and record it (`design_choices.py add <course> --rule <id> --choice "..." --said "..." --risk
"..."`) - checks then report it as their choice and nothing changes it back. The factory's way: their words go into
`FEEDBACK_LOG.md`. A check is never a reason to undo a person's wish.

## Owner decisions in force — every law, one line

Where any other text in this factory disagrees with a row below, **this table wins**. A row naming a script is that
script's rule: its finding is what you act on. Where a row is a default, it says what the exception needs. Use judgement
for what no row covers. Before bending a law, or when a request seems to collide with one, read it in full: L27 onwards
in `references/owner-decisions.md` (grep `## L45`), the older laws in `references/laws-in-full.md`; every law with its
reasons is in `docs/FACTORY_LAWS.md`, its history in `docs/LAW_HISTORY.md`.

| | The rule |
|---|---|
| **L1** | **The approved programme is law; minutes are its units.** An academic hour is what the programme says (never assume 60); each module's teaching time equals its allocated minutes exactly; what does not fit goes to the handout. `hours/scripts/check_hours.py` before believing any plan |
| **L2** | **Main ILOs copied verbatim** — never edited, renumbered or improved. A Sub-ILO's wording is never re-worded by the factory except through the expert-reviewed elevation of L69; a re-expressed one is `PROVISIONAL` until ratified and never renumbered where a trainee sees it. The programme governs; the IMO model course guides |
| **L3** | **Official hours never changed to fit a schedule**; no attendance, contact time or compliance record is ever made up |
| **L4** | **No source, no maritime claim.** Never fill a gap from memory; a stated gap is a good answer. Every claim proved in the course's knowledge base by the `fact-checker` before approval (`fact_check.py`) |
| **L5** | **Theory delivered as active learning** — aim for 80 % learner-active minutes (Track B, `data-active`); the programme's theory/practice split (Track A, `check_balance.py`) never changes; theory is never removed; never reach the target by renaming screens |
| **L6** | **Tablet-first, touch-first, offline** — targets ≥ 44 px, no hover-only control, nothing at class time needs a network |
| **L7** | Nothing is useless until you have grepped its id, class, label and filename across both terminals, the course and every generated script |
| **L8** | Explain and relocate; do not delete on a complaint. When the operator says remove it, remove it (after L7) |
| **L9** | Edit approved inputs in place; built output is regenerated from them (`content_script.py apply`) |
| **L10** | **Visible must be sufficient**: a line that refers to something names it on the same line; this outranks any word budget |
| **L11** | A generated file is never hand-edited (`DO NOT HAND-EDIT` header) — change its input or generator |
| **L12** | **Every asset has provenance, a licence and a look** (open every image); unclear rights are `RIGHTS_REVIEW_REQUIRED` and never ship (`check_assets.py`) |
| **L13** | A visual explains something, never decorates (`figure_why.py`, `check_kit.py`) |
| **L14** | Read only: the reference course and the Android app (`hooks/guard_writes.py`) |
| **L15** | A green exit is not proof — read the output; report failures as plainly as passes |
| **L16** | **The factory builds and reports; the owner approves, commits, publishes and installs** (exception: L70) |
| **L17** | Every screen looks composed (`audit_compose.js`) — a big empty box or a huddle in a corner is a defect |
| **L18** | **Content is locked, delivery is free** (`retrofit/knowledge/content-lock.json`): meaning, ILOs, hours, assessment intent, exercises, terms, facts and language need authorisation; screens, layout, visuals, animation, interaction and code are rebuilt freely. An old visual is a teaching decision: keep the decision, rebuild the implementation |
| **L19** | **Every course is in English**, never asked; the programme stays in its own language and is quoted in English; chat and notes follow the operator (`retrofit/scripts/check_language.py`) |
| **L20** | A figure that claims to move is proved alive (`GBVerifyFigures`); static is a defect for a dynamic idea |
| **L21** | **The Android app is a publish target, not a workspace** — read only until a person approves that course and version in their own words: *"Approved. Publish this course to the NOVIKONTAS training app."* (`publish.py --approved-by`) |
| **L22** | A slide is not an internal document — no file talk, sources, review notes or honesty markers on what a trainee reads (`check_slide_text.py`) |
| **L23** | A slide that has a picture leads with it; a slide whose words read on their own needs none (`check_visual_first.py`, L61) |
| **L24** | An expert's change is content: restyled, never rewritten by the factory; the operator may still change it (`detect_expert_edits.py`) |
| **L25** | **The reader does not work in IT** — see *Every reply to the operator* |
| **L26** | **The operator's request wins** — see above |
| **L27** | Three test levels, all on the **trainee tablet**: a self-check shows the trainee's own score; the **module check** shows the score - no pass mark and no PASSED / NOT PASSED; the **final assessment** is the only one with the pass mark (70 %) and is blind |
| **L28** | **Course type** `NEW_ENTRANT` / `EXPERIENCED` from intake shapes the build; never easier names — the professional terms, explained; every model-course instrument is assumed available; the school's simulators come from `coverage/knowledge/simulators.json` |
| **L29** | **A word-for-word content script** per module is approved before any HTML; the slides say exactly that (`check_script_match.py`) |
| **L30** | Module 1 is the pilot when built module by module; with agents or after the expert's Ready (L70) the Stage 2 `build_mode` answer rules (law text: `docs/FACTORY_LAWS.md`) |
| **L31** | Ask like a colleague — questions batched in one pop-up with options at the next STOP; honesty markers in `factory-notes.md`, never on a slide |
| **L32** | The course remembers — see below |
| **L33** | **Pictures: found before made** — knowledge base → old course → source files → internet → generated; small ones enlarged; equipment a trainee must recognise is a real photograph or a drawing, **never a generated picture**; a real photo still missing goes in `PHOTOS_TO_TAKE.md` — a list, never a stop or a question |
| **L34** | **One module per programme topic**, in its order, with its hours; never merged or split; the final assessment is the last module |
| **L35** | **Two tablets** — slides on the instructor's, tasks only on the trainee's, opened with **OPEN TASK** |
| **L36** | Enough theory before any task (`knowledge/theory-rules.json`, `content_script.py`) |
| **L37** | Every slide's picture slot is named — kind, what it shows, who makes it — or `none` when its words read on their own (`media-and-tasks.json`) |
| **L38** | **Tasks varied and hands-on, no typing**; every set varies by family - no two neighbours of one family, none over ~40 %, 3+ families in a set of 4+; a self-check has at most 2 basic tasks (choose, match, order); one team task a module (`content_script.py` `t_family_*`, `t_sc_mix`, `t_no_team`; `theory-rules.json` `task_variety`) |
| **L39** | A colleague gets only the HTML; the real-tablet test is the owner's, at the end |
| **L40** | **The factory works in `course\`**; the master folder's sources, knowledge base and old course are read only (`hooks/guard_writes.py`) |
| **L41** | The old course is the foundation — read whole at intake (`old_course.py`); each module says what it keeps, modernises and adds |
| **L42** | Tasks usable with zero tablet experience (`course-task-ux` §0, `check_task_pages.py`) |
| **L43** | Every module in its own folder, complete and offline (`check_module_folder.py`) |
| **L44** | Three places in `course\`: `to_review\`, `modules\`, `working_claude\` (`workspace.py tidy`) |
| **L45** | The classroom system's own rules (`knowledge/classroom-system.json`, `check_course_package.py`) |
| **L46** | **3D only where the figure's why is spatial, at full quality and smooth on the tablet** — no share and no cap |
| **L47** | **A generated picture only within the budget the operator said yes to** — one yes per course at Stage 2 (`intake.json` `picture_budget`); outside a course build the person says yes to each picture (`nano-banana`) |
| **L48** | Bloom measured, and lifted by the tablet — one level a course toward the outcome (`bloom/GUIDE.md`, `bloom_map.py`) |
| **L49** | 20 / 80 in class, every theory slide kept — theory-as-activity proposed per sub-topic at Stage 2 (`active/GUIDE.md`) |
| **L50** | A fix is not a build — find every place, one list, one yes, change, one check (`fix/GUIDE.md`, `fix.py`); after any fix the walk review runs on every touched slide (`fix.py check --kind walk`) |
| **L51** | Every picture opens full screen; every module closes with the same recap before its module check |
| **L52** | As many real photographs as possible; a source-book figure only once a named person cleared it (`check_assets.py clear`) |
| **L53** | Good padding; free space is a note — decks pass the overflow / collide audits and the figure's own EMPTY check (`audit_deck.js`, `audit_compose.js`) |
| **L54** | Every drawing whole and clean (`audit_drawing.js`) |
| **L55** | **Kit first, custom allowed, every figure has a teaching reason** — diagrams come from the figure kits (`course-visuals/kit/SPEC.md`); when no kit part shows the idea, a `"custom_figure"` is allowed; every figure carries `"why"` + `"why_text"` (`figure_why.py`, `check_kit.py`) |
| **L56** | A photograph carries what it shows and its credit into the full-screen view — no credit on the slide |
| **L57** | A drawing of real things carries their real photographs when the build sheet lists them (`"photo_row"`) or its why is real-thing-recognition - never unasked |
| **L58** | Every photograph once in the whole course - a repeat only when its slide says why (`"reuse_why"`) |
| **L59** | **No module before its map** — ILO map approved and the knowledge-base decision recorded (`course_gate.py`) |
| **L60** | No 3D scene is picked unasked - only where the slide's why is spatial (law text: `docs/FACTORY_LAWS.md`) |
| **L61** | **Every slide is one of the layout templates** (`course-module-ui/knowledge/layout-templates.json`), chosen by the compiler; a figure gets the share it needs (`layout_fit.py`), never squeezed. The compiler never cuts, moves or pages the words: the writer moves a long slide's words to the instructor as short points (`v_paged_slide`); no picture quota |
| **L62** | Repeats of a look, the dark share and the 80 % light ground are notes - the compiler never flips a layout to avoid a repeat (law text: `docs/FACTORY_LAWS.md`) |
| **L63** | Equipment drawn as it looks on board (`course-visuals/kit/PARTS.md`) |
| **L64** | A module in 30-40 min, its fixes in 20 — the pre-check first (`precheck.py`); a rebuild is a fix (`fix.py rebuild`); the minutes are a measure, never a reason to skip a check |
| **L65** | **A drawing that moves stays smooth** (`audit_motion.js`) |
| **L66** | Every item a simulator can train is trained on one (`coverage/SIMULATORS.md`, `sim_coverage.py check`) |
| **L67** | Every slide moves on Next where its picture has something to show; a 3D model of a flat idea is a must-fix (law text: `docs/FACTORY_LAWS.md`) |
| **L68** | The Instructor-Led Guideline — active means every trainee commits to an output; a passive run at most 15 min and 20 % of theory, or a one-line reason (`instructor_led.py check`); every course gets day sheets and the course on one page, never a clock time (`day_sheets.py`) |
| **L69** | **The experts get the pedagogy first** — Bloom now, Bloom proposed and the activities, before any script (`pedagogy_review.py`, `bloom/GUIDE.md` §5); every outcome is **raised or kept, one at a time** (`pedagogy_review.py next` / `propose` / `task`, `knowledge/ilo-elevation.json`) |
| **L70** | **Built after the expert's Ready** — the office PC builds unattended; see *Auto build* |
| **L71** | **Kept, lifted one level, seen whole** — the old course's order and theory kept; every claim proved; the build walks every Next (`fit_gate.py`); a module with no PASS is not done, nor without the **walk review** by an AI reviewer who did not build it (`walk_review.py`; two rounds, then the operator accepts on record or has it fixed) |
| **L72** | **Every finished course goes into the Course Libraries, with all its material** — `scripts/finished_course.py <course>` writes `Course Libraries\Finished courses\<Course name>\` (`trainee\`, `complete\`, `00_READ_ME.md`); run again after every release or fix |
| **L73** | **A doing outcome is practised, not only shown** — a Sub-ILO whose verb asks for Apply or higher needs an activity screen tagged to it or an exercise in `assessment_map.json`; slides and questions alone are a must-fix (`i_not_practised`, `content_script.py`) |
| **L74** | **No script before its sources** — every Sub-ILO of a module has a passage in the knowledge base (the programme, study plan and brief only name it); a gap stops `course_gate.py --module N` until sources are added, or the operator accepts it in their words (`kb_coverage.py check` / `accept --why --by`) |
| **L75** | Project work arrives with the course, only where the course has it — `working_claude\project_work.json` at Stage 2 (`project_work.py init`); a course with no project work gets no file and no check |
| **L76** | Every compiled course carries its overview for LND — `_course_shell\overview.json` and `_course_shell\materials\`, instructor-side only; the package check refuses a course without them (`course_overview.py`) |

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
| **ship** | put an **approved** course onto the terminals | `tablet/GUIDE.md`; `course-tablet-publisher` does it |
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
   **Read the old course whole** (`old_course.py inventory` and `images`). **No knowledge base?** Make it, unasked:
   `kb_tool.py build <folder> --course <course>` makes it with no window, in the background while the intake goes on
   (`kb/GUIDE.md`) — with the Course KB Builder program where it is on the computer, else with the factory's own
   builder, which fetches what it needs by itself; only when neither can run, `kb_tool.py find <folder>` — suggest one
   in plain words, its question in the pop-up. **The course libraries:**
   `course-visuals/scripts/subject_library.py ensure "<title, STCW ref, module titles>" --course "<course>" --json` —
   its subject library, then `common`, read before the knowledge base and the internet. Exit 3 with no match: choose
   `--subject-id`, `--name`, `--subject-words` from the programme and call again (the library is made, nothing asked);
   exit 3 with no Drive: go on without. Findings go back with `subject_library.py contribute`, which picks the library;
   the course is registered (`contribute register-course`) once its modules folder exists.
2. **Sort the sources** — `kb_tool.py sources <kb> --course <course>` (`kb/GUIDE.md`); several editions → one question.
3. **Ask what is missing, once**, in one pop-up of up to four questions: the programme (the one blocking answer), the
   knowledge base, the old course, the course type (the programme's pointer *Recommended*), editions, and in retrofit
   only when `detect_expert_edits.py` says `nothing-to-go-on`, whether anyone edited it by hand (L24).
4. **Record** in `working_claude\intake.json`; editions with `kb_tool.py decide`, the knowledge base with `kb_tool.py
   decision`. Never web-search during intake; `UNKNOWN` means asked and not known.

Corrections arrive in the operator's words ("too much text on screen 4"): act on them, never turn one into an interview.

## The gate — Stage 2, approved before anything is built

1. **Experts first (L69).** Bloom now, Bloom proposed and the activities, per topic, in `to_review\pedagogy\` (Word,
   HTML, PDF): judge each topic in `pedagogy_review.json` by `bloom/GUIDE.md` §5 - **one outcome at a time**:
   `pedagogy_review.py next`, answer that one with `propose` (raise, or keep with a code), then its `task`; never
   two at once, never a decision typed into the file - then `pedagogy_review.py check` and `render`; the experts answer in the training app's editor, live or staging (`course_portal.py create`, `push --pedagogy`, `pull`). **When `pull` (or `push`, or a build) prints a numbered list of courses in preparation, stop and ask the user which one - read them the list - then run again with `--site` / `--course-id`; never choose for them.**
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
6. **Project work (L75) - only when the course has it:** a project module where teams draw cards (Project Management,
   Information Technology: D1-D4 deck, E1-E4 engine, at most 3 teams a card). Then `scripts/project_work.py init <course>
   --departments Deck,Engine [--codes D1-D4,E1-E4] [--max 3]`; write each card (title, situation, task, data,
   deliverables) from the brief and the knowledge base with the module's script; the operator approves
   (`project_work.py approve --by`), uploads the Word cards to Drive and the links are recorded (`link`). Every build
   then writes the cards to `additional-materials\project-cards\` and `modules\classroom\projects.json`, so the imported
   course arrives with its projects: the instructor adds the trainees, presses Draw projects and Create trainee folders.
   A course with no project work has no `project_work.json` and gets none of this - never make one up.

## Stage 3 — the content script, approved before any HTML (L29)

`script/GUIDE.md` is the lane, `scripts/content_script.py` does it. Per module, in teaching order: **part 1, the
instructor tablet** — each slide's exact words, picture slot, minutes, notes, and a task slide with OPEN TASK where a
task begins; **part 2, the trainee tablet** — each task, one question a screen, answers, feedback, the trainee's own
score. Begin from the module's ILO map rows (`ilo_map.py show`), the old course's keep / modernise / add and the
knowledge base (`kb_tool.py search`). Before scripts are written in parallel, `STANDARDS.md` gets the course's
`## Ship profile`. Before each module is drafted, `instructor_led.py plan <course> --module N` picks its activity formats
by each Sub-ILO's task type (L68) - write the activities in them; a module that comes out one direction is a
must-fix - and each Sub-ILO's question mechanics (self-check, module check) - write the questions in them. Fix rounds
use `content_script.py check` (nothing written); `render` once, for the operator.

- **Proved (L4):** one `fact-checker` agent per module; approval is refused while a claim is unjudged or unproved.
- **Read cold:** one `task-readiness` agent per module (Haiku) answers each question from the slides before it only;
  what it cannot answer, or where it would not know what to do, is a must-fix until cleared (`script/GUIDE.md` §2).
- **Checked:** the theory, slide-text, pictures-and-tasks and ILO-map checks head the review page; a must-fix blocks
  approval (`--despite-findings` only on the operator's word). Questions carry `"sub_ilo"`, and `"bloom"` + `"bloom_why"`
  when written above their task type's level.
- **Reviewed as a page and a Word file:** the operator corrects by typing, by Word comment or in the chat; the
  operator-stated facts are listed once. The **Bloom card** (L48) shows each question's level and the share at *Apply*
  or higher (suggested 50 %) — suggestions only.
- **Shown before applied:** `read` / `propose` print what was understood; `apply --confirmed` only after the operator's yes. A written script changes only this way, never by editing `MNN.json`: a hand edit is missing from `FEEDBACK_LOG.md` and drops the approval. A trim the build asks for goes the same way.
- **Approved by the operator's own act:** `approve --by <name>` in their session; an unattended run builds `--draft`;
  never approve on an instruction relayed from another session. The one exception is the expert's Ready (L70).
- **Built, never typed:** the deck and task pages by `compile/scripts/compile_module.py`, the course's own pages and
  additional materials by `compile_course.py`. **One command builds and checks a module:** `compile/scripts/build_module.py
  <course> --module N` — start at the Quickstart of `compile/GUIDE.md` (a workflow's module builder reads
  `compile/BUILDER_CARD.md` instead, and nothing else); figure specs from `course-visuals/kit/CATALOGUE.md`.

## Building

`knowledge/build-order.json` is the authority for the order; the compiler keeps it for a module built from its approved
script (`build_module.py`).

- **Two phases:** Phase A with no agent — placeholders of each picture slot's shape and every check that does
  not need the pictures (`compile/scripts/phase_a.py`); Phase B fills the pictures from `MNN_VISUAL_NEEDS.md` and the
  photo catalogue. A placeholder never ships.
- **The look is routed:** `course-module-ui` (`design_system.py install`, `references/vocabulary.md`); to choose and fill
  a screen read one file, `course-module-ui/knowledge/blueprints.json`. GAS BASIC Module 1 is the visual reference,
  not a template: no fixed slide count, and low density is not low depth.
- **Done means PASS:** a module is built only when `build_module.py` printed PASS; the workflow blocks a module without
  one, and `course_portal.py upload` refuses while a module's last build failed.

## Auto build — after the expert's Ready (L70)

The watch looks at the queues of both sites, live and staging, and builds the course whose Ready queued it there; every
build (`build_module.py`) pulls the experts' answers first (`--no-pull` for offline work). A run from
`course_portal.py watch --once` (`NOVIKONTAS_AUTO_BUILD=1`) has nobody to answer:

- Carry out every expert note (`pedagogy_review.py check`) and write its `done`. Pass every STOP with the expert's name:
  `--approve --by "<expert> (Ready in editor)"`, `content_script.py approve ... --by "<expert> (Ready in editor)"`; the
  build plan question takes its first option.
- Never ask: a question goes to `working_claude/OPEN_EXPERT_QUESTIONS.md` with the choice made, and the build goes on.
- No paid pictures. Free sources first — Wikimedia Commons, DVIDS, USCG, NOAA, the old course, the knowledge base (the
  `visual-sourcer`; small ones enlarged) — then Nano Banana in the Gemini app if a signed-in browser is there
  (`gemini-browser`). `picture_briefs.py queue` / `place`. An unfilled space keeps its brief and does not stop the build.
- Build every module, compile COURSE.html, run the checks, fix what they find. Never push to git; never write outside
  the course folder.
- End with one line: `AUTO BUILD DONE`, `AUTO BUILD DONE - PICTURES PENDING: <n>` or `AUTO BUILD STOPPED: <why>`.

**After an attended session** the course goes up unasked: `course_portal.py upload --course <course>` is the last step
of a build and of `fix.py rebuild`; it imports a draft once nothing but picture spaces stops it, else says what does.

## Honesty markers

The markers (`UNKNOWN`, `PLACEHOLDER`, `PROVISIONAL`, `[VERIFY: <what>]`) are defined in `novikontas-course-start`.
Never invent regulatory content, hours, pass marks or citations; every marker used is listed in `factory-notes.md`.

## Verify before reporting done

`compile/scripts/build_module.py` builds a module, runs its checks (script match, navigation, audits, package, walk
review) and prints PASS. The sign-off of a build, a retrofit and the handover is the ordered list in
`references/verify-in-full.md` (hours, syllabus coverage, tablet verification, visuals, slide text, plain language, expert
edits last); a fix runs only the one check for its kind of change (`fix/GUIDE.md` §4). Read every output (L15). After a
change to the factory itself, `scripts/factory_trial.py run` builds the trial modules and scores them against the last trial.

Then write `templates/factory-notes.md` into the course folder: what was made, every marker with its source, the
achieved ratio, what moved to the handout and why, and a last section of **feedback on this skill** — written during
the run, never left for a human.

**A finished course goes into the Course Libraries (L72).** When the course is finished - and again after every release
or fix - run `scripts/finished_course.py <course folder> --name "<Course name>"`. It copies the delivered `modules\`
and `additional-materials\` to `Course Libraries\Finished courses\<Course name>\` (`--to`, else
`NOVIKONTAS_COURSE_LIBRARIES`, else the libraries' default places): `trainee\` holds only what a trainee sees or uses
(decks, handouts, self-checks, module checks without keys, day sheets, project pack, pre-brief cards), `complete\` holds
everything, instructor material included. Anyone building the trainee side gets the `trainee\` folder. A new kind of
instructor file must be added to the script's rules, never sorted by hand.
