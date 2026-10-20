# Owner decisions in force — Phase 5, every row in full

`SKILL.md` → *Owner decisions in force* carries the operative line of each row; this file is the row word for word,
as it stood in `SKILL.md` up to 2.50.4. **Where an older rule anywhere in this factory disagrees with a row, the row
wins.** The record behind the rows (the owner's words, the cases) is `references/laws-in-full.md` § Phase 5.

Read a row here before working on its step, and whenever an operator's request seems to collide with it. One
heading per law: grep `## L45` and read that section only.

## L27
**Built out in:** step 6

Three test levels, all on the **trainee tablet**: self-checks and the module check show the trainee **their own score** — it is for them and does not count; the **final assessment is the only graded test**. Every task opens only when the instructor opens it (L35); the instructor sees done / not done and the result as information, never pass/fail or red

## L28
**Built out in:** steps 2, 7

Course type `NEW_ENTRANT` or `EXPERIENCED` is declared at intake and shapes the build (new entrants: more explanation, more screens, more worked examples). **Never easier names** — every course uses the professional terms used on board and in the regulations, explained so a new entrant understands them and can explain their actions at sea (owner, 2.18.2). Every instrument and simulator in the IMO model course is assumed available — never asked

## L29
**Built out in:** now

Before any HTML, a word-for-word **content script** per module is approved by the operator; the slides then say exactly that. Facts the operator stated are listed there once per module, marked *operator-stated*, so they are checked before HTML — see *Stage 3* below

## L30
**Built out in:** step 10

**Module 1 is a pilot**, built by five roles and approved before any other module is built

## L31
**Built out in:** now

Ask like a colleague: real expert questions batched as **one pop-up with options** at the next STOP, then carry on. No "needs SME review" spam. Honesty markers live in `factory-notes.md`, never on a slide, never a reason to stop; "next" at a STOP ratifies what it showed

## L32
**Built out in:** now

`COURSE_STATE.md` updated at the end of every stage; every operator correction in `FEEDBACK_LOG.md`; a pattern file offered when the operator is happy — see *The course remembers* below

## L33
**Built out in:** step 8

Pictures: KB → old course → source files → internet → authored → generated; keep legit old schematics; **every picture in the knowledge base and the old course is usable as it is** (credited where known, listed); what is missing is **searched on the internet and downloaded** into the course folder, the download list confirmed once per module (owner, 2.19.0); equipment a trainee must recognise is **never** an AI image — schematic plus the "photos to take at Novikontas" list

## L34
**Built out in:** now (2.17.0)

**One module per programme topic** — in the programme's order, with the programme's hours (GAS BASIC: 22 teaching modules). The programme's final-assessment topic is the **last module, and the assessment only**: no slides, no teaching. Topics are never merged or split. An academic hour is the programme's; at Novikontas 40 min when it is silent

## L35
**Built out in:** now in the script and architecture; the app's change list in step 6

**Two tablets.** The slides run on the instructor tablet, mirrored to the classroom screen; the notes stay on the instructor's panel. Tasks are **only** on the trainee tablet. At task time the slide only says a task starts now and what it is about, and the instructor's panel has one button, **OPEN TASK**; the task then opens on every trainee tablet by itself. No task list, no browsing, no "all tasks" or "back to tasks" button

## L36
**Built out in:** now (2.17.0)

**Enough theory before any task.** A slide carries the teaching itself, not a headline; the notes carry what the instructor explains; a module's words fill its minutes; a self-check comes only after a block of new theory; every answer is taught before its task opens. Floors: `knowledge/theory-rules.json`, checked on the content script; since 2.26.0 (L49) theory comes in ~5-minute cycles and the words-per-minute floor counts plain theory only

## L37
**Built out in:** now in the script and architecture; built in steps 8-9

**Every slide leaves room for its picture** and names it: the kind (photograph, schematic, cutaway, chart, step / flow / process animation, interactive diagram, 3D model, 3D scan, video, AI illustration ...), what it shows, the layout - and **who makes it**: the factory, the image/video generator (context only), the sources, **Novikontas** (a photo, a film, a phone 3D scan) or outside help. 40+ min of theory: something that moves, turns or can be explored. `knowledge/media-and-tasks.json`

## L38
**Built out in:** now in the script and architecture; built in step 6

**Tasks are varied and hands-on** - 19 ways of answering, none typing: choose one / all, choose-and-justify, order, match, sort, complete the sentence, tap the place, label the drawing, find the hazards, read the instrument, set the value, operate the panel, scenario - and since 2.28.0 (L49) find the fault, spot the errors, build the plan, rebuild the incident, compare (`course-task-ux` §2a). A self-check uses 2+, a module check 3+; "choose one" at most 40 %; one hands-on question per module

## L39
**Built out in:** now (2.18.1)

**Who tests where.** The build makes every file ready for the tablet system; a colleague gets **only the HTML**, to check in their own browser; **the real-tablet test is the owner's, at the end**. Instructor notes are short points in `instructor_notes/M01_INSTRUCTOR_NOTES.md`, for the panel - never on a slide (2.18.1). Pictures have no quota: every chance to show the theory is taken, and the picture floors are suggestions

## L40
**Built out in:** now (2.19.0)

**The factory works in `course\`** beside the operator's material: the folder given is the master folder (source_files, knowledge base, old course - read only); everything the factory makes goes into `course\` next to them. `scripts/workspace.py`; every tool accepts either folder

## L42
**Built out in:** built in step 6

**Trainee-tablet tasks are modern, exciting, and usable with zero tablet experience** - a first *try the tablet* screen; tap and drag only (drag also tap-then-tap); an animated hand shows each new gesture once; big controls (56 px), big text; instant, alive feedback; real equipment in 3D and working panels; forgiving, no timers, no error messages. `course-task-ux` §0

## L43
**Built out in:** built in steps 6-10

**Every module in its own folder** - `course\modules\M01_<title>\` holds everything it needs (presentation, tasks, instructor files, every asset and script), reaches nothing outside it, fetches nothing; `START_HERE.html` opens the presentation straight away; `START_HERE_EXTENDED.html` has a button for the presentation, every task, the module plan, the notes. `scripts/check_module_folder.py`

## L44
**Built out in:** now (2.20.0)

**Three places in `course\`:** `to_review\` - only what the operator checks (architecture page, content scripts and their Word files, instructor notes); `modules\` - the finished modules; `working_claude\` - everything only the factory uses (state, logs, notes, data, checkpoints - all kept). Nothing loose. An older course: `scripts/workspace.py tidy`

## L45
**Built out in:** built in steps 6-10

**The course folder is built to the classroom system's own rules** (`knowledge/classroom-system.json`, from the owner's `COURSE_FACTORY_PROMPT.md`): `course\modules\` = COURSE.html + `_course_shell\course_map.js` + `module01\` ... each with `presentation\index.html` (every `.slide` with `data-title`, the instructor notes in `data-cue`, a task slide with `data-activity` + `data-task-href`), `tasks\sc1_<slug>.html`, `assessment\check.html`; task pages report `gb-task-done`; module checks PASSED / NOT PASSED (for understanding, not an official grade); no spaces, ≤ 15 MB a file, offline; 1280 × 800 landscape. `scripts/check_course_package.py` runs the list and the classroom's own importer. **Rulebook of 2026-10-12 (2.23.0):** team tasks (`data-mode="team"` + `task-mode` / `task-scope` metas, `gb-team`), answers marked by `data-key`, never readable; no link into a `_` folder. **2026-10-19 (2.50.3):** the result screen is the last screen - nothing to press, no link; a task never leaves its own page.

## L46
**Built out in:** now (2.22.0); built in step 9

**3D where it makes sense - at most half of the presentation's teaching slides - at full quality, and smooth on the tablet** (owner, 2026-10-07: *"don't make it in all slides ... but also don't cut quality, and put it only on slides where it makes sense, not only because you can"*). 3D for equipment and structures whose shape, inside or layout in space is taught - not charts, symbols, documents or ideas. The cap is on how many, never how good. Speed from how scenes run, never a lesser look: one shared renderer, scenes built when their slide comes and freed after, no frame while nothing moves, soft shadows worked out once while still, pixel ratio min(device, 2); 30 frames a second with the CPU slowed 4x. `knowledge/media-and-tasks.json` → `three_d`; `content_script.py`, `check_course_package.py` (each `.slide` carries `data-visual`)

## L47
**Built out in:** now (2.24.0)

**A generated picture only after the person described it and said yes** (owner, 2026-10-14: about €0.10 a picture, four developers redoing them use the budget up). Places first (`scripts/picture_briefs.py list`); one place at a time, eight plain questions with a suggestion each (`knowledge/media-and-tasks.json` → `generation_brief`); the prompt shown; generated once on a yes - the nano-banana tools refuse without the person's words; a redo needs a new yes; the count and cost said every time

## L48
**Built out in:** now (2.25.0)

**The Bloom level is measured, and the tablet lifts it** (owner, 2026-10-15: *"bloom taxonomy needs to be on higher level - that's why we have tablets"*). Every ILO's level read from its verb, every task's from how it is answered (`knowledge/bloom.json`); the Stage 2 page and every Stage 3 review page show where the course is, every task below its Sub-ILO, and the tablet task types that would lift it - **suggestions only**; Main ILOs stay verbatim (L2), a weak Sub-ILO verb is re-expressed with the operator's approval. Read `bloom/GUIDE.md` when judging or lifting a level; `scripts/bloom_map.py`

## L49
**Built out in:** now (2.26.0-2.28.0)

**20 / 80 in class - the programme unchanged, every theory slide kept** (owner, 2026-10-15). On paper the programme stays (L1); in class plain theory - the instructor explaining - aims at a fifth of the minutes, the rest the trainees do something: tasks, practice, simulator, and slides marked `"active"` (explain-then-reveal, predict-then-reveal, worked-example, scenario, explore). **Theory is never removed to get there** - a plain slide keeps its words (it can be read, the instructor moves faster) and gives up minutes; good theory may be added. Theory in ~5-minute cycles before a task. Measured on the Stage 2 page (theory-as-activity with minutes) and every Stage 3 review page - a suggestion, never a stop. `knowledge/theory-rules.json` → `split`. **The factory proposes, the operator decides** (2.27.0): per sub-topic, how its theory is learned by doing - written for a maritime expert, not an IT person - each kept or struck on the Stage 2 page; only kept ones are built. Read `active/GUIDE.md` at Stage 2; `scripts/active_plan.py`. **Five new tablet tasks** for the higher Bloom levels (2.28.0): find the fault, spot the errors, build the plan, rebuild the incident, compare

## L50
**Built out in:** now (2.29.0)

**A fix is not a build - find, one list, one yes, change, one check** (owner, 2026-10-15: *"i want for fixes to be faster and still quality ... it will not go to 3-4 qa reviews"*). A correction to built modules - one, some or all - reads only `fix/GUIDE.md`, COURSE_STATE and the course's `STANDARDS.md`; "find it in the others" is one sweep of every module (`scripts/fix.py sweep`, measured in a hidden browser by `scripts/measure_slides.py`); the operator says yes once for the whole list; words go through every content script in one batch and into the built slides; a part every module uses is changed once and copied (`sync-shared`); a wish for every module becomes a standard; then **one** check for the kind of change, by whoever made it - no QA agent after the fixer, no whole-course QA, at most 2 agents. `knowledge/fix-rules.json`

## L51
**Built out in:** now (2.30.0)

**Every picture opens full screen, and every module closes with the same recap** (owner, 2026-10-15: *"all images, every picture, illustration, explanitory image ... can be clicked and be full screened, and later you can close it"*; *"before [the module check] it should be beautiful summary in same design ... boxes, main points what to take away from this module, and all modules should be same closing slide design"*). **The picture viewer** `gb_zoom.js` + `gb_zoom.css` (course-module-ux assets, copied by `design_system.py`) on every page that shows a picture - deck, tasks, module check, handout: tap opens, X / tap outside / Esc / swipe down / Back / the next slide close, pinch or + / − zoom; a picture the trainee answers on gets a corner ⤢ button so a tap stays the answer. **The recap**: one slide `"recap": true` straight before the module check's task slide, 3-6 points "Short title - one sentence", built in the one shared design `.slide.dark.recap` (`gb_compose.css` 15 - animated boxes, then "Next: the module check"). `content_script.py` (r_ findings), `check_course_package.py`. Both are **design**: a person who wants them otherwise is told the risk and gets their way (L26)

## L52
**Built out in:** now (2.25.1)

**As many real photographs as possible** (owner, 2026-10-15) - in the presentation and the trainee tasks. Wherever a camera can show it: the slide's picture, or a small real photo beside the drawing (build sheet `inset`); KB, old course, source files first, then free-licensed and credited; missing ones on the "photos to take at Novikontas" list; never AI for equipment a trainee must recognise (L33). Checked on the script: `v_few_photos`

## L53
**Built out in:** now (2.25.1, 2.26.3)

**No empty space, good padding** (owner, 2026-10-15). Pictures take the room the words leave, words at reading size, padding and the chrome's safe area kept, nothing spills. The deck is compiled from the shared layouts (`compile/GUIDE.md`) and passes `audit_compose.js`, `audit_deck.js`, `audit_collide.js` before it is shown. **Inside the figure too** (operator, 2.26.3): a figure fills its panel (`audit_drawing.js` EMPTY), sits beside its words at reading size (`two-col`, not a stage over small cards), and every line a step lights is a tap target for that step

## L54
**Built out in:** now (2.25.2)

**Every drawing whole and clean** (owner, 2026-10-15). A part inside a hull, tank, room or box stays inside its real shape (slope, curve - follow it or clip to it); nothing cut off at the drawing's frame, also in a later step; every label 4 px clear of other shapes, lines and labels and of its own box's edge; an intentional crossing marked `data-may-cross` / `data-no-contain` / `data-may-overlap`. `audit_drawing.js` before a deck is shown; `gb_fit.js` in every compiled deck

## L55
**Built out in:** now (2.26.0)

**Figures come from the figure kit** (owner, 2026-10-15). A system, state, flow or sequence is a `NAME.kit.json` spec in `working_claude\figures\MNN\` (`course-visuals/kit/SPEC.md`), never a one-off SVG. A part the kit lacks is made to `kit/PARTS.md` in the module's `assets\kit_parts.js` and used at once; **after the module is complete** `kit/scripts/kit_parts.py promote` puts it in the factory's kit and the merge request goes to the owner (ask the operator before the push). Parallel build: module agents write only their own `kit_parts.js`; the orchestrator promotes at assembly

## L56
**Built out in:** now (2.27.0, 2.33.0)

**Every photograph carries what it shows into the viewer - unasked** (operator, 2026-10-15, from Aigars's review: *"images expandable, a lightbox with more explanation about the photo"*; *"the factory needs to make it on its own"*). One viewer, L51's `gb_zoom.js`, in every compiled deck too: full screen shows a photo's record under it - what it shows (its `description` in `_photo_meta.json`: write it when the photo comes in, for a trainee, claiming only what the picture shows) and its credit. No build-sheet key; a photo without a description is reported at build. A generated picture keeps its full record but shows no credit and no label, and is never an L57 thumbnail

## L57
**Built out in:** now (2.27.0)

**A drawing of real things carries their real photographs - unasked** (operator, 2026-10-15: *"an illustration like this would also have a real image of it, smaller, close, which you can click"*). The compiler finds the real things a drawn slide names (its line terms, the drawing's own labels) and puts their photos in a row under the drawing - numbered like the drawing, each opening in the L56 panel, at most four - matched by the photo's `shows` in `_photo_meta.json` (write it whenever a photo comes in). A cleared photo of another module is copied in; one awaiting rights review never. A real thing with no photo is reported and listed in `working_claude\PHOTOS_TO_TAKE.md` - never blocks the build

## L58
**Built out in:** now (2.27.0)

**Every photograph once in the whole course** (operator, 2026-10-15: *"don't have duplicate images - either a different one or none, on all modules"*). One photograph, one screen - slide picture, inset, photo in a drawing or L57 thumbnail; a copy under another name in another module is the same photograph (`url_or_origin`, else the bytes). A thumbnail takes a different photo or none (the thing goes on `PHOTOS_TO_TAKE.md`); one placed by hand twice, or later than a module that already shows it, is reported at build - choose a different one or none. Build every module again after photos change

## L59
**Built out in:** now (2.42.0)

**No module before its map** (owner, 2026-10-16: *"before creating any module the AI should have already made the ILO mapping and suggested for KNOWLEDGE_BASE to be created"*). Before any module's content is written, the course has its ILO map (`working_claude/ilo_map.json`), approved on the Stage 2 page, and a recorded knowledge-base decision; when there is no knowledge base, the factory suggests making one, unasked. Every Sub-ILO is taught on a slide and checked by a question, and every fact traces to a listed source. `scripts/course_gate.py` stops `content_script.py` and `compile_module.py --init-build` without them; `script/GUIDE.md` §0

## L60
**Built out in:** now (2.49.7)

**At least one 3D scene in every module where the subject allows it - strongly recommended** (Aleksis, 2026-10-19: *"it should be like it is very recommended to build a 3d model at least once where you can in a module"*). A script with no 3D slide is no reason to skip it: `compile_module.py --init-build` picks the best slide unasked (a shape, an inside or a layout in space; never a real photo's slide) and writes its starter scene entry from IGF M03's `m03_station3d.js`. A module built with no scene is said loud - the build's RECOMMENDED block and its own card on the review page, naming the best candidate and why. Never a block (2.18.1): the operator declines with their reason, `"declined_3d"` at the top of the build sheet, and it is not proposed again. A slide the script plans as 3D given a 2D figure stays a must-fix until its own `"declined_3d"` holds a reason. L46's limits and `compile/GUIDE.md` 2b's speed and tap rules unchanged

## L61
**Built out in:** now (2.52.0)

**Physical equipment is drawn as it looks on board** (Aleksis, 2026-10-20, approving the realistic kit mock-up: *"yes we like this new kit styling"*; *"also do the Parts added from courses"*; *"make the ship look realistic aswell, look at real images of it"*). Every figure-kit part that is a physical thing is drawn in its material, with light and shade and its real features (flanges, saddles, a dome, an actuator or a handwheel, a bedplate, a ship's plating and superstructure); screens stay flat ISA-101 and diagrams stay diagrams; the teaching state stays readable and amber / red stay for alarm / trip. The kit does it in every deck - no option, no per-slide ask. A new part declares its `look` and an `equipment` part draws with `KIT.h.body` / `KIT.h.equip` and the kit's materials (`course-visuals/kit/PARTS.md`, `check_kit.py`).

## L41
**Built out in:** now (2.19.0)

**The old course is the foundation.** Read it whole at intake (`scripts/old_course.py inventory`, and `images` for its pictures); at the Stage 2 STOP every module says what it **keeps**, what it **modernises and makes digital**, and what it **adds**
