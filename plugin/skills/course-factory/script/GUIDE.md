# Stage 3 — the module content script, word for word (L29)

Read this lane when a module's words are written, corrected or approved. **Nothing is built in HTML
until the operator has approved the script.** One script per module, plus one for the final
assessment (`--module final`). Everything is done with `scripts/content_script.py`; the check that the
built module obeys it is `scripts/check_script_match.py`.

## 0 · Before writing — the ILO map, the model course, the old course, the knowledge base

Before any module the ILO mapping is made and a knowledge base is suggested. **A module is written against what it owes,
never from memory.** `content_script.py` will not render or approve a script (exit 2) until the course has its ILO
map, the Stage 2 page is approved with it, and the knowledge-base decision is recorded:

```
python scripts/course_gate.py <course> --module 4        open, or exactly what has to happen first
```

Then, before the first screen is written, read — in this order, and only these:

1. **The module's rows of the ILO map** — `python scripts/ilo_map.py show <course> --module 4`: the
   programme topic and the **Main ILO verbatim (L2)**, every **Sub-ILO** the module owes (kept /
   re-expressed / added), and the model-course items under the topic. The same module in
   `working_claude/architecture.json` says how they were planned (active learning, media, tasks).
   **The outcome review of the module** - its rows in `working_claude/pedagogy_review.json`: the level each outcome was
   raised to or kept at (`proposed.level` - the level the module teaches and checks to, not the verb's), the task
   decided for it (`proposed.how`, the expert's own when `task_expert`), and the experts' answers and notes. An approved
   script records what it was written against (`based_on`); when a Sub-ILO or a row changes after that, `status`,
   `render` and every build stop and name it - change the script to match and approve it again.
2. **The model-course items it owes** — the course's transcribed syllabus (`working_claude/*syllabus*.json`,
   `coverage/GUIDE.md` §1), the items listed by `ilo_map.py show`. They are the outcomes *inside* the topic;
   `coverage/` checks them later against everything built.
3. **The old course's keep / modernise / add for this module (L41)** — `architecture.json` →
   `from_old_course`, and `OLD_COURSE_INVENTORY.md` for the slides and pictures it names. **A course rebuilt from an
   old one keeps the old course's order and what each old slide explained** (`old_course_inventory.json` holds each
   slide's words): write the module in the old order, keep the old explanation in sentences and lift the Bloom level and
   the delivery around it. The check says it (`old_course_findings`): a slide earlier than the old order needs
   `"moved_why"` with the expert's reason; an old slide that taught something and is left out goes in the script's
   `"dropped_old"` (`[{"from": "<deck>.pptx, slide 27", "why": "..."}]`); the slides must show at least 60 % of the
   old slides' words, and every number and key term of each old slide they cite (on screen or in the cue).
4. **The course libraries first** (`intake.json` → `subject_library`; the Gas Library for every gas course,
   then Common): `python <course-visuals>/scripts/subject_library.py
   find "<the slide's subject>" --course "<course>"` — the shared topic and which module of each course teaches it, the
   **cited facts**, glossary, regulations held, reference PDFs with their distribution, and passages from
   every course's knowledge base at once (file + page). Quote a value only with its source. **A row marked
   CONFLICT is not settled**: do not pick one of its values — name the conflict on the screen's notes and
   in `"sources"`, and point to the library's `OPEN_DECISIONS.md`; the course owners decide. An inbox row
   (NEW) is not reviewed: check its source before using it. No library on this computer: skip this.
5. **The knowledge base — only through `kb/scripts/kb_tool.py search`** (several phrasings: the other
   names, the abbreviation, the older term). Never open a whole `document.md`. A declined knowledge base
   (the Stage 2 page says so) means the source files themselves, searched the same narrow way.

While writing:

- **Every Sub-ILO is taught on at least one slide and checked by at least one question.** Mark the slide(s)
  that teach it `"sub_ilo": "4.a"` (a list when a slide teaches two), and **every question** with the
  Sub-ILO it checks. A Sub-ILO with children (4 → 4.a, 4.b) is met through them.
- **Every fact on a slide traces to a source in `"sources"`**: the document, its edition, the section or page
  (`"IGF Code 2016 (MSC.391(95)): 6.7.1, 15.8.2"`). Only the current edition is cited (intake). An
  operator-stated fact goes in `operator_facts`, not in `sources`.
- **Save back what the libraries did not have**: a fact you verified in a source, with
  its document, edition and page, that `find` did not return — `subject_library.py contribute --course "<course>"
  fact "<subject>" "<value, unit, conditions>" --source "<doc, edition, page>" --found-for "<course> M04 s03"`;
  a term with its regulation's definition — `... term "<term>" "<meaning>" --source "<...>"`; a regulation —
  `... regulation "<title>" "<edition, what it requires>" --source "<...>"`. The client picks the library
  (a convention's material goes to Common) and says which.
  They go to the library's inbox as NEW for the course owners to review, never straight into its facts.
  An operator-stated fact is not contributed. Say in the module's report what was contributed.

The review page's **ILO map and sources check** — must-fix findings, like the theory check — lists a Sub-ILO
taught nowhere or checked nowhere, a question with no `"sub_ilo"`, a `"sub_ilo"` the module does not own, and
an empty `"sources"`. Approval waits for them unless the operator approves `--despite-findings` (L26). A
script approved before this gate existed keeps its approval; its findings are reported, never forced (`OPERATOR.md`).

The ILO map's slide and question rows are **built from the scripts**, not typed per module: after a script is
approved or its slides move, `python scripts/ilo_map.py refresh <course> [--module N]` writes each row's
`where_taught` / `checked_by` from the `"sub_ilo"` tags (the approved Main ILO and Sub-ILO wording is never touched).

**The module's activity formats come before its words (L68).** A course where every practical is solo or pair project work
is narrow, so the module varies its formats. Before drafting a module run `python scripts/instructor_led.py plan <course> --module N`: each
Sub-ILO's task type (its verb, or the register's) picks one or two TLAs of the guideline's pool, varied across the module,
with how each is written (`instructor-led/GUIDE.md` §0). Write the module's active slides and activity screens in those
formats: a decision as a case dilemma (`"active": "scenario"`), a refutation (`"claim"`), a contrast pair or a worked
example; a real-time outcome as an activity `"format": "scenario-run"` with its `"events"`; a hands-on one as
`"demonstration"` or `"planted-defect"` at the equipment; a team outcome as `"closed-loop"` or `"challenge-response"`
with observers and a trainee-led debrief. An activity screen's `"roles"`, `"safety"`, `"observe"` and `"events"` are the
words its practical's cards are drafted from - approved with the script; a simulator or real-equipment activity states its
`"safety"` here, from the material. The check is a must-fix when the module came out one direction anyway (two activity
screens of one format, or three practice moments of one format - `a_one_direction`) or a team, real-time or hands-on
Sub-ILO has no activity of its kind (`a_type_unserved`); `"formats_why"` at the top of the script keeps both a note.

**A doing outcome is practised, not only shown (L73).** An outcome with an action verb - "perform" and the like - cannot
be taught from slides; something else is needed. Every
Sub-ILO whose verb asks for Apply or higher (build, make, prepare, perform, plan, present ... - `knowledge/bloom.json`, or
`"bloom"` written on its row) gets at least one activity screen tagged to it (`"kind": "activity"`, `"sub_ilo"`) where the
trainee does the thing on a real case - builds the Gantt, prepares the budget, carries out the procedure - or an exercise
`assessment_map.json` assigns to it in this module. Slides explain it and questions check it; neither practises it. A
module without one is a must-fix (`i_not_practised`), and the admin's ILO map shows the row as "Slides only".

**No script before its sources (L74).** Before a module's script is written, `scripts/kb_coverage.py check
<course> --module N` (also inside `course_gate.py --module N`) searches the knowledge base for every Sub-ILO with the
programme's sub-topic wording - the programme, study plan and expert brief left out, since they only name the subject.
A sub-topic with no passage is a gap, and the gate stops: add sources for it to the course material folder and run
`kb_tool.py build` again, or record the operator's own answer (`kb_coverage.py accept <course> --module N --ids 2.4
--why "..." --by "..."`). Never write the script first and look for sources afterwards: the claims then have nothing to stand on.

## 1 · Write the script

`<course>/working_claude/script/M01.json` — the whole lesson **in the order it is taught**. It runs on two
tablets (L35), and the script says which screen is where:

- **Instructor tablet** - `slide`, `task-slide` and `activity` screens: what the classroom screen shows,
  with the notes on the instructor's panel. A task is **never** on a slide. Where a task begins there is
  a `task-slide`: its words only say that a task starts now and what it is about; `"opens"` names the
  task; on the instructor's panel it is the OPEN TASK button, and its `minutes` are the task's time.
- **Trainee tablet** - `self-check`, `module-check` and `final` questions, each with `"set"` (SC1, SC2 …,
  MC, FA). A set's questions come **straight after** the task slide that opens it. One question per
  screen; at the end the trainee sees their own score - it is for them, and a self-check or module
  check never counts (L27). No task list, no browsing, no "back to tasks".
- `minutes_allocated` is the module's minutes from the programme (L1, L34); the instructor-tablet
  minutes must add up to it exactly.

```json
{"module": 1, "title": "<module title, course language>", "course_language": "English",
 "operator_language": "lv", "status": "draft",
 "operator_facts": [{"fact": "<what the operator said>", "where": "s03", "said": "2026-10-01"}],
 "sources": ["<document, edition: sections or pages>", "…"],
 "screens": [
  {"id": "s01", "kind": "slide", "title": "…", "text": "line one\nline two", "sub_ilo": "1.a",
   "visual": "<the picture planned, and where it comes from>", "notes": "<instructor only>", "minutes": 5},
  {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - …",
   "text": "<only: a task starts now, and what it is about>", "notes": "…", "minutes": 4},
  {"id": "q01", "kind": "self-check", "set": "SC1", "sub_ilo": "1.a", "question": "…", "options": ["…", "…", "…"], "correct": "A",
   "feedback": "<what the trainee sees after answering>", "mechanic": "tap to choose"},
  {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - …", "text": "…", "notes": "…", "minutes": 6},
  {"id": "m01", "kind": "module-check", "set": "MC", "sub_ilo": "1.b", "question": "…", "options": ["…", "…"], "correct": "B",
   "feedback": "…", "mechanic": "tap to choose", "graded": false}]}
```

- `text` is the **exact visible words** of the slide, not a description of them. One line per line.
- **Groups of trainees.** When one class holds two or more groups that learn the same theory but are
  checked differently (ship technicians and ship navigators), the script says so at the top:
  `"groups": {"T": "Ship technicians", "N": "Ship navigators"}` - any ids, two or more, each with the name the
  trainee taps (in the course language). A `self-check`, `module-check` or `final` question with `"group": "T"` is
  asked only of that group; a question with no `group` is asked of everyone. Slides, task slides and activities never
  carry a group - they are the same for all. On the tablet the set opens on *Which group are you in?* (one big
  button per group); the choice is kept on that tablet for the course and can be changed until the first Check; the
  trainee is numbered and scored over the questions they saw, and the result the instructor gets carries the group.
  The task rules are counted **per group** - each group's own path through a set (the questions for everyone plus
  its own) must have the self-check's and module check's question counts and ways of answering, Part A then Part B,
  single choice at most 40 % and a hands-on question in the module; every group has a question in every set. The
  review page and the Word file mark each question *Only for: <group>*. A final with groups is one blind page per
  variant that branches the same way (FA, FB stay re-sit variants - see `compile/GUIDE.md`).
- **The recap closes the module (L51).** The slide straight before the module check's task slide is the
  recap: `{"id": "s24", "kind": "slide", "recap": true, "title": "What to take away", "text": "Kept liquid - cold,
  under pressure, or both
...", "visual_kind": "none", "notes": "...", "minutes": 2}` - 3 to 6 points, one line
  each, *"Short title - one sentence"*, 24 words or fewer, the module's main points in the words its slides used.
  The slide word target does not apply to it; the notes range does. It is built in the one shared design (every
  module the same). Missing or misplaced, it is a must-fix - unless the person chose otherwise after hearing the
  risk (L26, `design_choices.py`), and then approval passes and names their choice.
- **20 / 80 in class (L49).** A slide where the trainees do something gets `"active"`:
  `explain-then-reveal`, `predict-then-reveal`, `worked-example`, `scenario` or `explore` (they work the
  model or diagram themselves) - and its notes say what they do. Never mark a slide that is only shown.
  The review page shows plain theory against active minutes (aim: 20 / 80). To get there, **keep every
  theory slide** and give the plain ones fewer minutes and the minutes to activity; never remove good theory - its
  words stay, on the screen or, as short points, said by the instructor. Theory may be added.
- **Compact, never cut.** When a slide holds more than its screen does, keep every
  fact and change its form: short points with the full words in the instructor's cue (`"points"`, the text stays), a
  table (`"value | what it means"`), a labelled figure, numbered steps, or a second slide (`"parts"`). Never drop a
  number, a name or a reason to make it fit. A course rebuilt from an old one is checked for it: every number and key
  term of an old slide (its numbers, its abbreviations, the words it says twice) still appears in the new slides that
  cite it, on screen or in the cue (`o_lost`, a must-fix), and the slides still show at least 60 % of the old slides'
  words (L71).
- **A worked example before every task that works something out.** A calculation, a value to set, or any task at
  Apply or higher (`bloom_map.task_level`) comes after a slide on the same Sub-ILO that works one with the room - a
  worked example (`"active": "worked-example"`, `"ask"`, `"reveal"`), or a scenario with the why of each choice. The
  rule stated alone is not enough (Project Management M03: the cash-balance rule on a slide, the sum never worked, then
  a task asking for a balance of -3,000). Missing, it is a must-fix: "no worked example before ..." (`t_no_worked_example`).
  A calculation's own words are judged too when its answer is only new numbers. A slide of short points teaches its full
  words - the instructor says them - but a task's key term must be on one of its points (`t_term_not_shown`).
- **Pick the slide for the information.** The templates hold no words of their own. Read what each
  piece of the module's information is, and write it in the shape its template needs - the compiler then builds that
  template (`course-module-ui/knowledge/layout-templates.json` "picking"). Every new word is drafted from this course's
  own material (its slides, its sources, the operator's facts) and goes on the review page for approval like the text;
  none is a stock phrase.

  | The information | Write it as | The slide |
  |---|---|---|
  | **the default for a plain slide** whose words on screen pass the target (`theory-rules.json` `slide`) - a long explanation, with a picture or without | `"points"`: short points, one a line, shorter than the text (`theory-rules.json` `points`); `text` keeps the full approved words - the instructor says them (`data-cue`) | short points, beside the picture or alone |
  | a calculation or a reading | `"active": "worked-example"`, lines `"what you do \| what you get"`, `"ask"` the room's turn, `"reveal"` its answer | worked example, then your turn |
  | a common wrong belief | `"claim"` the belief, `"claim_is"`: `"false"` (or `"true"`), the lines say why | true or false, then why |
  | what to do when something happens | `"active": "scenario"`, the lines the situation, `"ask"`, `"choices"` (2-4, one a line), `"why"` (one for each), `"right"` (its letter) | what would you do? |
  | parts of equipment taught earlier | `"ask"` ("Name each number."), the part names as lines; the build sheet's `"spots"` on a static 3D render or a photo | name the parts |
  | several limits or values | 3-8 lines `"value \| what it means"`, no picture | numbers to remember |
  | two states of the same thing | the first line `"A \| B"`, each line after it `"what \| in A \| in B"`; build sheet `"figure"` and `"figure_b"` | spot the difference |
  | the end of the module | the recap, and `"asks"`: one question for each of its lines | the summary asks first |
  | just before a self-check | `"before"` on its task slide: 2-4 things to check, one a line | the list on the task slide |
  | a guess or a finding before the answer | `"active": "predict-then-reveal"` or `"explain-then-reveal"`, the lines the situation, `"ask"`, `"reveal"` (one line or several; both, never one - on a `"points"` slide the room's turn shows under the points) | the lines, then the question, the answer on the last Next (the worked-example template) |
  | before the module check, every second or third module | `"drill"`: `quick-fire` (lines `"prompt \| answer"`), `say-it` (the situation, `"ask"`, `"reveal"`) or `find-it` (lines "Point to ...", `"spots"`); `"seconds"` 5-120 | a quick drill |

  Each template's slots and what fills them, in one line: `course-module-ui/knowledge/blueprints.json`.
  A picture and a short explanation, two pictures, numbered steps and three parts of one system keep the templates
  they had (`compile/GUIDE.md` §2, §2h). A drill comes after the
  module's last teaching slide; minutes are the module's as before (L1). `content_script.py` checks each shape
  (`shape_problems`). Beside a picture a scenario's situation, its question, choices and whys, and a worked example's
  lines and question each hold a measured number of words (`theory-rules.json` `beside_picture`, `t_overfull`) - trim the situation
  and give the explanation to the instructor (the notes' `Say:`), never cut the teaching.

  **The check reads the plain slides for you.** A slide left as ordinary lines beside its picture is read by
  `content_script.template_findings`: when its words already have the shape of a template - a question to the room, a
  situation, a wrong belief, a calculation, steps in order, two or three headed groups, lines `Label: text`, a number on
  every line - the review page says which template, and the exact fields or build-sheet `"blocks"` to write
  (`t_fits_template`, a suggestion). When more than 60 % of a module's teaching slides are plain and some of them fit a
  template, the module is a must-fix that names those slides (`t_template_mix`): write them as suggested until the module
  is at 60 % or under, or say why it stays plain - `"plain_why"` at the top of the script - and it is a note. A module
  where no plain slide fits a template gets a note only. The sign words are English; a course in another language is read
  by the shape of its lines (`layout-templates.json` `"mix"`).
- **3D and AI pictures.**
  - **3D** only where the figure's why is spatial - a shape, an inside or a layout in space (a tank and its barriers, a
    space and what is around it, a pipe between its valves); set the slide's `visual_kind` to `model_3d` and describe the
    scene in `visual`. A 3D model of a flat idea is a must-fix; the factory picks no scene unasked.
  - **AI picture:** where a slide sets a scene or a situation that no real photograph shows (people at work, an
    operation, an incident) - `ai_illustration`. It sets a scene only; the pictures are made within the course's one
    approved budget (nano-banana, L47).
- **Bloom (L48).** A question says which Sub-ILO it checks (`"sub_ilo": "1.2"` - expected on every
  question, §0), and - only when
  it is written above its task type's usual level - its level and why (`"bloom": 4, "bloom_why": "..."`).
  The review page then shows every question below its Sub-ILO and how the tablet would lift it.
  Aim the tasks at the Sub-ILO's level, and above *Remember* wherever the content allows (`bloom/GUIDE.md`).
- **Less on the slide, the explanation in the notes (L36, `knowledge/theory-rules.json` - every number is there).**
  The trainee looks at the slide and listens to the instructor at the same time: the slide shows the picture and the
  key facts, numbers and names in clear, readable words; the notes carry the full explanation the instructor gives.
  The words a slide holds, and how the check treats each limit (stated here and nowhere else):

  | On the slide or in the notes | Limit | Severity |
  |---|---|---|
  | words the trainee reads on a plain slide (the title and the lines, or the title and the points) | about 45 | note: write it as short points |
  | words beside a picture (measured at 1024 x 768; the room's question, choices and steps counted on their own) | 75 | must-fix (`v_paged_slide`) |
  | words in the instructor notes of a slide | 20 to 150 | note |

  A plain slide whose words on screen pass 45 becomes a slide of short points (`"points"`, the table above):
  the full approved words stay in `text` and go to the instructor's panel - moved, never cut. The module's slides and
  notes together fill its PLAIN theory minutes (an active slide's minutes are what the trainees do). A self-check
  comes only after a block of new theory (short cycles, L49), and every question's correct answer must already be in
  the slides before it - write the slide that teaches it first, then the question. A module with less theory than
  that has no self-check; its module check covers it.
- Course text (titles, text, questions, answers, feedback) is in COURSE_LANGUAGE; the notes on the
  page and in the Word file around it are in the operator's language.
- **Instructor notes are labelled lines**, one a line, 20 to 150 words (the table above):
  `Say:` the full explanation the instructor gives, in full sentences, `Ask:` the question to the room, `Show:` what to
  point at on the picture: `"notes": "Say: <the explanation, in full sentences>\nAsk: <the question>\nShow: <the place on the
  picture>"`. They reach the instructor's panel as the slide's
  `data-cue` (`render` also writes `to_review/M01_INSTRUCTOR_NOTES.md` for the review); they are never on a slide.
- Kinds: `slide`, `task-slide`, `activity` (instructor tablet); `self-check`, `module-check`, `final`
  (trainee tablet). Module checks are never graded (L27) and come at the end of the module; a
  final-assessment script (`--module final`, the last module, L34) holds a task slide and `final` questions.
- **A team task** (the classroom rulebook 4b) is a task slide with `"team": {"size": "3", "roles":
  ["Leader", "Recorder", "Checker"], "scope": "team"}` - `"3-4"` for a range; `"scope"` `team` (one answer per team)
  or `member` (everyone answers, the team's average shown); roles are optional. The review page and the Word file say
  it in a line under OPEN TASK; changing it goes through the chat, like the way a question is answered. A module check
  and the final assessment are always answered alone. Its code on the tablets is TT1, TT2 ...
- Every fact the operator stated is listed once, at the top of the review — from `operator_facts`
  and from `FEEDBACK_LOG.md` rows marked *operator-stated* for this module.
- NEW_ENTRANT or EXPERIENCED changes how much is explained and how (`knowledge/course-type.json`).

### Pictures, and how the trainee answers (L37, L38)

`knowledge/media-and-tasks.json` is the list, and who makes each thing. On every **slide**:

- `"visual_kind"` — `photo`, `annotated_photo`, `photo_to_take`, `technical_drawing`, `schematic`,
  `cutaway`, `chart`, `comparison`, `step_animation`, `flow_animation`, `process_animation`,
  `interactive_diagram`, `model_3d`, `model_3d_scan`, `model_3d_licensed`, `video_real`,
  `video_generated`, `ai_illustration` — or `none`, only on the closing summary. Pick it from what the
  slide must teach (`course-visuals`, `decide/knowledge/learning-needs.json`): what moves or changes state
  is animated; what has an inside is a cutaway or a 3D model; what a trainee must recognise on board is a real photograph
  (the course's own, reused, enlarged) or a drawing, never a generated picture; a real photo still missing is listed in
  `PHOTOS_TO_TAKE.md` - a list, never a stop (L33).
- `"from_old"` (L41; on every slide of a course rebuilt from an old one) — where in the old course the slide comes
  from and what changed: *"1. Liquefied Gas tankers.pptx, slides 37-40 - the photographs became a 3D model"*, the deck's
  file name and its slide numbers as written there. Shown on the review page and read by the order check.
- **What a question asks, a slide has shown.** A task's answer, and the answer to the room's own question (`ask` /
  `reveal`), must be in the words the slides up to it put on screen - their lines, or the points of a slide of short
  points. The instructor's notes do not count: the trainee never sees them.
- **Every value from a source the course holds (L4).** A number with its unit on a slide (a pressure, a temperature, a
  limit) must be in the course's retrieval packs, its knowledge base, the old course, the programme or the operator's
  stated facts - `fact_findings` refuses one found in none of them. Search first (`kb_tool.py search`, the subject
  library's `find`), then write the source's value.
- `"visual"` — what it shows and why, in one or two sentences; `"layout"` — `split` (text left, picture
  right), `visual_wide` or `visual_full`.
- **`"picture"` — the slot, fixed here:** `{"kind": "photo|figure|3d|none", "aspect": "4:3", "shows": "<what it
  must show>"}` on every slide but the recap, and on every question answered on a picture. The kind follows the visual:
  a real picture (photo, document drawing, film still, generated) is `photo`; **one photo shows one thing** - several
  of a sort (four kinds of gas carrier, ships A to F) go in `"items": ["LPG carrier", "Moss LNG carrier", ...]`, each
  found or made on its own and shown as a tile; a schematic, cutaway, chart, comparison or
  animation is `figure`; `model_3d*` is `3d`. It decides the slide's layout before anything is built, so the build's first
  phase needs no agent (placeholders of this shape, compile/GUIDE.md 2g), and the course photo catalogue matches photos
  to it by `shows`. Must fix: an unknown kind, a kind the visual does not need, a photo or figure with no aspect, nothing
  it must show. A script from before the slot existed is read from `visual_kind` and `visual` (a reminder, never a block).
- **The words a layout holds are a must-fix here**, not a build-time note (the limit beside a picture is in the table
  under *Less on the slide*; `layout-templates.json` "budgets", `compile/GUIDE.md` §2). The factory never
  pages or cuts words by itself, so the writer makes them compact - short points (`"points"`, the full words to the
  instructor), a table, a labelled figure, numbered steps - or gives the slide `"parts"` in the build sheet; every fact
  stays (compact, never cut, §1).
- **The course's ship.** STANDARDS.md may carry a `## Ship profile` section - `- Pump arrangement: deepwell pumps`,
  `- Not on board: pump room, cargo pump room` - and render then says (a note) every screen that names what the course's
  ship does not have (chem advanced: four scripts written in parallel set scenes in a "pump room" on a deepwell-pump ship).
  Write the profile at Stage 2, before the scripts are written in parallel.
- **No quota:** wherever a picture, an animation or a realistic 3D illustration can show what the slide
  teaches, put it in. A slide with none, a long module where nothing moves, few kinds of picture - these come
  back as suggestions, never blocks; nothing is added only for variety (L13).
- **3D: only where the figure's why is spatial, at full quality** (L46, L67) - no share and no cap. Each 3D model is a main
  picture: true proportions, real materials, labels, a cut-open view where the inside is taught. The built slide carries the kind as `data-visual="model_3d"`, so the finished deck is counted too.

On every **task question**, `"mechanic"` is how the trainee answers. `knowledge/media-and-tasks.json` lists every mechanic
with its family and the exact format of its `"answer"` (one box, one line per item, `*` marking what is right).
`single_choice`, `multi_select` (`"correct": "A, C"`) and `read_instrument` use `options` + `correct`; the rest use
`"answer"`. The interactive types, how each looks on the tablet and an example of each: `course-task-ux` §2b and
`course-task-ux/templates/interact/example_set.json`.

Every question gets a `"brief"`: one short line said when the answer is wrong - why it is not right, never which answer is
("That is the boiling point of another cargo.", not "It is -42 °C."). The right answer is shown in the debrief, where the
class checks it together. Add `"confidence": true` to a Part A choice to ask how sure the trainee is. `hotspot`,
`label_diagram`, `spot_the_hazard`, `read_instrument`, `set_value` and `panel_operate` also name their picture
(`visual_kind`, `visual`).

**Vary the tasks by family, not by name (`theory-rules.json` `task_variety`).** Match, sort and order are three names and
one way of answering - dragging cards - so every set (self-check, module check, final) is counted by family
(`media-and-tasks.json`: choose, decide, arrange, locate, operate, investigate, build): no two neighbouring questions of
one family, no family over about 40 % of the set, and at least three families in a set of four or more. Write each
self-check as Part A - quick questions that check what was taught (Bloom 1-2), at least one on a Sub-ILO from an earlier
block - then Part B: one harder task the trainee works out alone (Bloom 3+), on a rich mechanic: one that locates,
operates, investigates or builds, a scenario or a prediction, or anything on a 3D model or an animation (a subject with no
equipment has them too: spot the error in a real document, check a colleague, find the fault, build the plan, fill the
matrix). A self-check keeps at most two basic questions (the choose and arrange families) - a must-fix; the family rule
itself is a note: follow it, the build is not stopped by it. Every module has a hands-on question (locate, read, set,
operate, scenario), and the mechanic that looks like the job is the one to pick: a valve line-up for a valve question, a
detector display for a reading, the GA drawing for "where is it".

**Make it engaging.**
- Part B works on the module's running case - the group's own ship, project or company - not a new example each time.
- A choice has a consequence: a scenario that shows what happens, a prediction against the real data.
- Give them something real to work on: a filled-in document with errors, a photograph to inspect, a reading to take.
- Mix the families across the module: a document to check, a plan to build, a picture to tap, a value to set.
- One team task a module where a Sub-ILO is Bloom 3+ (a module of 90 minutes or more without one gets a note,
  `t_no_team`): a team case, plan or drill with roles (Leader, Recorder, Checker), in place of one self-check's Part B -
  a task slide with `"team": {"size": "3", "roles": ["Leader", "Recorder", "Checker"], "scope": "team"}` that opens its
  own set (`TT1`). Module checks and the final are answered by each trainee alone.

**Clear what to do.** The task page says under every question what the trainee does (a multi-select how many to tap, a
calculation its unit and rounding). The question itself asks one thing (two question marks are a must-fix), a
calculation names its unit and how to round in the question or in `"unit"` and `"rounding"` (a must-fix), and a negative
question writes NOT or EXCEPT in capitals (a note).

## 2 · Show it to the operator

**First, proved in the sources (L4).** Once a module's script is written, the `fact-checker` agent (one per module, in parallel) proves every claim in the course's knowledge base: `scripts/fact_check.py` finds the claims and proves what a source says word for word, the agent judges the rest found / partly / not found from the source passages only, and leaves a change list that cuts what no source says and corrects what it says otherwise - proposed with `content_script.py propose`, shown like any correction (an unattended build applies it itself, `fixes --apply`, each change logged for the expert). Approval is refused while a claim is not judged or one not proved is still in the script (a course with no knowledge base is not checked).

**Then, read cold** (not theory about addition and then a test on multiplication and division). The
`task-readiness` agent (one per module, beside the fact-checker; it runs on Haiku - cheap) is a trainee who read only
the slides before each self-check and module-check question: `content_script.py readiness <course> --module 1` gives it,
per question, those slides' words and the question, never the answer. It tries to answer each one and lists what it
cannot answer from those slides alone, with the missing piece, and where it would not know what to do (the action not
said, a multi-select without how many, a calculation without its unit or rounding, two asks in one, a NOT not stressed,
an option that gives the answer away), each with its fix; `readiness --record` keeps them beside the script
(`working_claude/script/M01.readiness.json`). Each is a must-fix in the theory check of the review page until the writer
changes the script and runs the agent again (or writes in the finding's `cleared` what was changed).


```
python scripts/content_script.py render <course> --module 1
```

writes `to_review/M01_SCRIPT_REVIEW.html` (opens with a double-click, prints to PDF) and
`to_review/M01_SCRIPT.docx`, both in two parts: **part 1, the instructor tablet** (every slide, and the
OPEN TASK button on each task slide) and **part 2, the trainee tablet** (every task, one question per
screen, each showing the slide that teaches its answer). At the top: the module in numbers - minutes
against the programme's, words per theory minute - and the findings of both checks. It writes
`to_review/M01_SCRIPT.docx` — **the operator's copy is the Word file**. Every
editable text is its own grey box, locked against deletion, open for typing. Fix every problem
`render` lists before showing it.

## 3 and 4 · Corrections and approval

Corrections (`propose` / `apply`), approval (`approve`) and what the three checks run on are in `OPERATOR.md`. Two rules
bind the writer here: nothing a script's words say changes without the operator's yes, and **approval is the operator's
own act - never an agent's, never relayed**. An unattended run builds with `compile_module.py --draft`, stops at the draft
and says in its report which scripts wait for approval; the one exception is the build after the expert's Ready (L70).
`check_script_match.py` fails a build from a draft.

## 5 · Building from it, and proving it

**The deck is compiled, not typed:** `compile/GUIDE.md`. The marks below are what the compiler
writes.

The screen inventory is **derived from the approved script** — not a separate approval. Every screen
built from it carries its id, and every approved text its field:

```html
<section class="slide" data-script="s02">
  <h2 data-script-field="title">…</h2>
  <p data-script-field="text">…</p>
<div data-script="q01"> <p data-script-field="question">…</p>
  <button data-script-field="opt.A" data-correct="true">…</button> <p data-script-field="feedback">…</p>
```

```
python scripts/check_script_match.py <course> --module 1
```

fails a changed word, a missing line, an extra sentence on a slide, a screen not built, a wrong
correct answer, and any module built from a script that is not approved. The header band, source and
credit lines, text inside drawings and controls are not script text; anything else that is not script
text is marked `data-script-ignore`, and the report counts it for QA. A better wording found while
building goes back to the operator as a proposed change to the script — it is never just built.
