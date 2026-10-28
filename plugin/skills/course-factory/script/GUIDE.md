# Stage 3 — the module content script, word for word (L29)

Read this lane when a module's words are written, corrected or approved. **Nothing is built in HTML
until the operator has approved the script.** One script per module, plus one for the final
assessment (`--module final`). Everything is done with `scripts/content_script.py`; the check that the
built module obeys it is `scripts/check_script_match.py`.

## 0 · Before writing — the ILO map, the model course, the old course, the knowledge base (2.42.0)

Owner, 2026-10-16: *"before creating any module the AI should have already made the ILO mapping and
suggested for KNOWLEDGE_BASE to be created"*. **A module is written against what it owes, never from
memory.** `content_script.py` will not render or approve a script (exit 2) until the course has its ILO
map, the Stage 2 page is approved with it, and the knowledge-base decision is recorded:

```
python scripts/course_gate.py <course> --module 4        open, or exactly what has to happen first
```

Then, before the first screen is written, read — in this order, and only these:

1. **The module's rows of the ILO map** — `python scripts/ilo_map.py show <course> --module 4`: the
   programme topic and the **Main ILO verbatim (L2)**, every **Sub-ILO** the module owes (kept /
   re-expressed / added), and the model-course items under the topic. The same module in
   `working_claude/architecture.json` says how they were planned (active learning, media, tasks).
2. **The model-course items it owes** — the course's transcribed syllabus (`working_claude/*syllabus*.json`,
   `coverage/GUIDE.md` §1), the items listed by `ilo_map.py show`. They are the outcomes *inside* the topic;
   `coverage/` checks them later against everything built.
3. **The old course's keep / modernise / add for this module (L41)** — `architecture.json` →
   `from_old_course`, and `OLD_COURSE_INVENTORY.md` for the slides and pictures it names.
4. **The subject library first, when the course is on its subject** (2.52.0; `intake.json` →
   `subject_library`; the Gas Library for every gas course): `python <course-visuals>/scripts/subject_library.py
   find "<the slide's subject>"` — the shared topic and which module of each course teaches it, the
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
- **Save back what the library did not have** (on its subject): a fact you verified in a source, with
  its document, edition and page, that `find` did not return — `subject_library.py contribute fact
  "<subject>" "<value, unit, conditions>" --source "<doc, edition, page>" --found-for "<course> M04 s03"`;
  a term with its regulation's definition — `... contribute term "<term>" "<meaning>" --source "<...>"`.
  They go to the library's inbox as NEW for the course owners to review, never straight into its facts.
  An operator-stated fact is not contributed. Say in the module's report what was contributed.

The review page's **ILO map and sources check** — must-fix findings, like the theory check — lists a Sub-ILO
taught nowhere or checked nowhere, a question with no `"sub_ilo"`, a `"sub_ilo"` the module does not own, and
an empty `"sources"`. Approval waits for them unless the operator approves `--despite-findings` (L26). A
script approved before 2.42.0 keeps its approval; its findings are reported, never forced (§4).

The ILO map's slide and question rows are **built from the scripts**, not typed per module: after a script is
approved or its slides move, `python scripts/ilo_map.py refresh <course> [--module N]` writes each row's
`where_taught` / `checked_by` from the `"sub_ilo"` tags (the approved Main ILO and Sub-ILO wording is never touched).

## 1 · Write the script

`<course>/working_claude/script/M01.json` — the whole lesson **in the order it is taught**. It runs on two
tablets (L35, owner 2026-09-30), and the script says which screen is where:

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
- **The recap closes the module (L51, 2.30.0).** The slide straight before the module check's task slide is the
  recap: `{"id": "s24", "kind": "slide", "recap": true, "title": "What to take away", "text": "Kept liquid - cold,
  under pressure, or both
...", "visual_kind": "none", "notes": "...", "minutes": 2}` - 3 to 6 points, one line
  each, *"Short title - one sentence"*, 24 words or fewer, the module's main points in the words its slides used.
  The slide word floor does not apply to it; the notes floor does. It is built in the one shared design (every
  module the same). Missing or misplaced, it is a must-fix - unless the person chose otherwise after hearing the
  risk (L26, `design_choices.py`), and then approval passes and names their choice.
- **20 / 80 in class (L49, 2.26.0).** A slide where the trainees do something gets `"active"`:
  `explain-then-reveal`, `predict-then-reveal`, `worked-example`, `scenario` or `explore` (they work the
  model or diagram themselves) - and its notes say what they do. Never mark a slide that is only shown.
  The review page shows plain theory against active minutes (aim: 20 / 80). To get there, **keep every
  theory slide** and give the plain ones fewer minutes - the words stay to be read - and the minutes to
  activity; never shorten or remove good theory. Theory may be added.
- **3D and AI pictures - planned unasked (2.49.0, operator 2026-10-16: "make it so they add 3D + AI generated photos
  when needed").** Before the review page is shown, plan them yourself - the operator never has to ask:
  - **3D:** where a slide's lesson is a shape, an inside or a layout in space (a tank and its barriers, a space and
    what is around it, a pipe between its valves), set its `visual_kind` to `model_3d` and describe the scene in
    `visual`. Aim for one good 3D scene in a module whose subject is spatial; none in one that is not (procedures,
    charts, ideas). L46 still holds: at most half the teaching slides, never a real photo replaced, full quality.
  - **AI picture:** where a slide sets a scene or a situation that no real photograph shows (people at work, an
    operation, an incident) - `ai_illustration`; (2.73.2) equipment too, first generated, then fixed. Planning it is
    free; the pictures are made within the course's one approved budget (nano-banana, L47).
  - The review page names what you left out as proposals (`v_3d_propose`, `v_ai_propose`): the slide and the words
    that made it. Each one the operator keeps goes into the script (propose / apply); each one they strike goes into
    the script's `"declined"`, outside the approved words, so it is never proposed again:
    `"declined": {"3d": {"s06": "operator: the comparison drawing is enough"}, "ai": {}}`.
  - A 3D proposal needs the shape in the slide's **title or planned picture** (two fit words at least), not only
    in its text, and none of: a sequence, a document or an idea there (steps, procedure, report, permit,
    checklist, model, layers of protection, "in turn"), a flow or process animation, a generated picture, or a
    worked example whose text is a list (2.49.2, `knowledge/media-and-tasks.json` `three_d`).
- **Bloom (L48, 2.25.0).** A question says which Sub-ILO it checks (`"sub_ilo": "1.2"` - expected on every
  question since 2.42.0, §0), and - only when
  it is written above its task type's usual level - its level and why (`"bloom": 4, "bloom_why": "..."`).
  The review page then shows every question below its Sub-ILO and how the tablet would lift it.
  Aim the tasks at the Sub-ILO's level, and above *Remember* wherever the content allows (`bloom/GUIDE.md`).
- **Enough theory (L36, `knowledge/theory-rules.json`).** A slide carries the teaching itself - the facts,
  numbers, names and reasons its Sub-ILO needs - not a headline (50-150 words, title included); the notes
  carry what the instructor explains, adds or asks beyond it (30 words or more); the module's slides and
  notes together fill its PLAIN theory minutes (25 words a minute or more - an active slide's minutes are
  what the trainees do). A self-check comes only after a block of new theory (5 min and 125 words since the
  last task - short cycles, L49), and every question's correct answer
  must already be in the slides before it - write the slide that teaches it first, then the question.
  A module with less theory than that has no self-check; its module check covers it.
- Course text (titles, text, questions, answers, feedback) is in COURSE_LANGUAGE; the notes on the
  page and in the Word file around it are in the operator's language.
- **Instructor notes are short** (2.18.1): two to four points per slide, one per line starting `- `, 10-50 words -
  what to ask, the one example to give, what to stress. The theory is on the slide. `render` writes them to
  `to_review/M01_INSTRUCTOR_NOTES.md` for the instructor's panel; they are never on a slide.
- Kinds: `slide`, `task-slide`, `activity` (instructor tablet); `self-check`, `module-check`, `final`
  (trainee tablet). Module checks are never graded (L27) and come at the end of the module; a
  final-assessment script (`--module final`, the last module, L34) holds a task slide and `final` questions.
- **A team task** (2.23.0, the classroom rulebook 4b) is a task slide with `"team": {"size": "3", "roles":
  ["Leader", "Recorder", "Checker"], "scope": "team"}` - `"3-4"` for a range; `"scope"` `team` (one answer per team)
  or `member` (everyone answers, the team's average shown); roles are optional. The review page and the Word file say
  it in a line under OPEN TASK; changing it goes through the chat, like the way a question is answered. A module check
  and the final assessment are always answered alone. Its code on the tablets is TT1, TT2 ...
- Every fact the operator stated is listed once, at the top of the review — from `operator_facts`
  and from `FEEDBACK_LOG.md` rows marked *operator-stated* for this module.
- NEW_ENTRANT or EXPERIENCED changes how much is explained and how (`knowledge/course-type.json`).

### Pictures, and how the trainee answers (L37, L38 — 2.18.0)

`knowledge/media-and-tasks.json` is the list, and who makes each thing. On every **slide**:

- `"visual_kind"` — `photo`, `annotated_photo`, `photo_to_take`, `technical_drawing`, `schematic`,
  `cutaway`, `chart`, `comparison`, `step_animation`, `flow_animation`, `process_animation`,
  `interactive_diagram`, `model_3d`, `model_3d_scan`, `model_3d_licensed`, `video_real`,
  `video_generated`, `ai_illustration` — or `none`, only on the closing summary. Pick it from what the
  slide must teach (`course-visuals`, `decide/knowledge/learning-needs.json`): what moves or changes state
  is animated; what has an inside is a cutaway or a 3D model; what must be recognised on board is the course's own
  photograph (reused, enlarged) or a photorealistic generated one - never a photo to take (L33, owner 2026-10-28).
- `"from_old"` (optional, L41) — where in the old course the slide comes from and what changed: *"1. Liquefied Gas
  tankers.pptx, slides 37-40 - the photographs became a 3D model"*. Shown on the review page.
- `"visual"` — what it shows and why, in one or two sentences; `"layout"` — `split` (text left, picture
  right), `visual_wide` or `visual_full`.
- **`"picture"` — the slot, fixed here (2.73.0):** `{"kind": "photo|figure|3d|none", "aspect": "4:3", "shows": "<what it
  must show>"}` on every slide but the recap, and on every question answered on a picture. The kind follows the visual:
  a real picture (photo, document drawing, film still, generated) is `photo`; a schematic, cutaway, chart, comparison or
  animation is `figure`; `model_3d*` is `3d`. It decides the slide's layout before anything is built, so the build's first
  phase needs no agent (placeholders of this shape, compile/GUIDE.md 2g), and the course photo catalogue matches photos
  to it by `shows`. Must fix: an unknown kind, a kind the visual does not need, a photo or figure with no aspect, nothing
  it must show. A script from before 2.73.0 is read from `visual_kind` and `visual` (a reminder, never a block).
- **The words a layout holds are a must-fix here (2.73.0)**, not a build-time note: beside a picture a slide's lines go
  into parts of at most 75 words (1024 x 768, layout-templates.json "budgets"); the build can put lines in parts but never
  cut one, so a single line over 75 words must be split in the script.
- **The course's ship (2.73.0).** STANDARDS.md may carry a `## Ship profile` section - `- Pump arrangement: deepwell pumps`,
  `- Not on board: pump room, cargo pump room` - and render then says (a note) every screen that names what the course's
  ship does not have (chem advanced: four scripts written in parallel set scenes in a "pump room" on a deepwell-pump ship).
  Write the profile at Stage 2, before the scripts are written in parallel.
- **No quota** (2.18.1): wherever a picture, an animation or a realistic 3D illustration can show what the slide
  teaches, put it in. A slide with none, a long module where nothing moves, few kinds of picture - these come
  back as suggestions, never blocks; nothing is added only for variety (L13).
- **3D: at most half, only where it makes sense, at full quality** (L46, owner 2026-10-07: *"don't make it in all
  slides ... but also don't cut quality"*). At most half of the presentation's teaching slides are `model_3d`,
  `model_3d_scan` or `model_3d_licensed` (must fix once there are two or more). 3D is for what has a shape, an inside or a layout in space - tanks, hull sections, pumps,
  valves, manifolds, piping, an enclosed space; a chart, a table, a symbol, a document or an idea (Swiss cheese, the
  steps of a risk assessment) is a drawing, a chart or an animation. Not more than two 3D slides in a row. Each 3D
  model that stays is a main picture: true proportions, real materials, labels, a cut-open view where the inside is
  taught. The built slide carries the kind as `data-visual="model_3d"`, so the finished deck is counted too.

On every **task question**, `"mechanic"` is how the trainee answers. `single_choice`, `multi_select`
(`"correct": "A, C"`) and `read_instrument` use `options` + `correct`; the rest use `"answer"` — one box,
one line per item, `*` marking what is right:

| mechanic | `answer` |
|---|---|
| `order`, `label_diagram` | one item per line (for `order`, in the right order — the tablet shuffles) |
| `match` | `left = right` per line |
| `categorise` | `Group: item; item` per line |
| `cloze` | the sentence, each gap `[right* \| wrong \| wrong]` |
| `hotspot`, `spot_the_hazard` | one area per line, the right one(s) `*` |
| `choose_and_justify` | options + correct for the action; `answer` = the reasons, the right one `*` |
| `set_value` | `-42 °C ± 3, range -170 to 20` |
| `panel_operate` | `control = end state` per line |
| `scenario` | `situation => right action* \| wrong \| wrong` per step |
| `true_false` | `statement => why` per line, the true ones `*` (2.74.0, Part A) |
| `critique` | `claim => right correction* \| wrong` - a claim that is right: `claim => * \| decoy \| decoy` (every claim the same number of choices; the tablet adds "keep it" to each) |
| `calculate` | `0.84 % vol ± 0.02`, then `! what the device shows` and `# the \| data \| sheet` lines |
| `predict` | `13.7 ± 1.5 @ 40`, `x: name \| unit \| low \| high`, `y: ...`, `given: x \| y \| label`, `curve: x y; x y` |
| `explore` | `find: the challenge => x > 9.5 and x <= 15` (a choice's name; `hide <readout>`) - the model is the build sheet's |
| `investigate` | options = the conclusions; `TAG \| title: what it says` per source, the relevant ones `*` |
| `line_up` | `goal: from => to`, `keep out: name; name`, `TAG: valve name = open \| shut` (as found) |
| `inspect_round` | `thing: what you see when you look`, the problems `*` |
| `take_apart` | `part: name: what it is`, `find: question => part`, `set: instruction => position` |
| `test_atmosphere` | `space: name \| depth`, `levels: 2; 8; 14`, `O₂ % \| 20.9 @ 0; 19.2 @ 14 \| below 19.5` |

**Part A, then Part B (owner, 2026-10-28 - 2.74.0).** Write each self-check as Part A - quick questions that check what
was taught (Bloom 1-2), at least one of them on a Sub-ILO from an earlier block - then Part B: one harder task the
trainee works out alone (Bloom 3+). Every question gets a `"brief"`: one short line said when the answer is wrong - why
it is not right, never which answer is ("That is the boiling point of another cargo.", not "It is -42 °C."). The right
answer is shown in the debrief, where the class checks it together. Add `"confidence": true` to a Part A choice to ask
how sure the trainee is. The ten interactive types, how each looks on the tablet and an example of each:
`course-task-ux` §2b and `course-task-ux/templates/interact/example_set.json`.

`hotspot`, `label_diagram`, `spot_the_hazard`, `read_instrument`, `set_value` and `panel_operate` also
name their picture (`visual_kind`, `visual`). A self-check uses 2+ mechanics, a module check 3+,
`single_choice` is at most 40 % of the module, and every module has a hands-on one (locate, read, set,
operate, scenario). Prefer the one that looks like the job: a valve line-up for a valve question, a
detector display for a reading, the GA drawing for "where is it".

## 2 · Show it to the operator

```
python scripts/content_script.py render <course> --module 1
```

writes `to_review/M01_SCRIPT_REVIEW.html` (opens with a double-click, prints to PDF) and
`to_review/M01_SCRIPT.docx`, both in two parts: **part 1, the instructor tablet** (every slide, and the
OPEN TASK button on each task slide) and **part 2, the trainee tablet** (every task, one question per
screen, each showing the slide that teaches its answer). At the top: the module in numbers - minutes
against the programme's, words per theory minute - and the findings of both checks. It writes
`to_review/M01_SCRIPT.docx` — **the operator's copy is the Word file** (owner, 2026-09-30). Every
editable text is its own grey box, locked against deletion, open for typing. Fix every problem
`render` lists before showing it.

## 3 · Corrections — understood first, applied only on yes

The operator corrects in the Word file (typing in the boxes, or Word comments), in a PDF, or in
the chat.

```
python scripts/content_script.py read <course> --module 1 [--pdf <file>]      Word file / PDF
python scripts/content_script.py propose <course> --module 1 --changes c.json  chat corrections
```

A chat `changes.json` is a list, applied in order (a later entry may edit a screen an earlier one added).
Besides editing one field of a screen it can add a screen, remove one, or change a top-level field:

```json
[ {"field": "q04.feedback", "new": "Membrane tanks are supported by the hull."},
  {"add_screen": {"id": "q06", "kind": "self-check", "set": "SC1", "mechanic": "single_choice", "question": "...",
                  "options": ["...", "..."], "correct": "A", "feedback": "..."}, "after": "q03"},
  {"remove_screen": "q05"},
  {"script_field": "sources", "new": ["IGC Code 2016: 1.2, 4.21-4.24"]} ]
```

`add_screen` takes `"after"` or `"before"` (a screen id; neither = at the end) and needs a new `id` and a
`kind`. `script_field` may be `title`, `minutes_allocated`, `sources`, `pass_mark` (a whole number 1-100)
or `operator_facts`; anything else (`status`, approval, `module`, `screens`) is refused — "Stopped -", exit 2,
nothing written. Problems the changed script would have that it does not have now (a self-check left
without its task slide, minutes that no longer add up) are listed under the changes, not blocking.

Both write a **pending list** and print what was understood — *"screen 7: the slide text: 'rely on'
becomes 'are supported by'; question 3: the correct answer becomes B"*. **Show that list to the
operator, in their language, and wait.** Then:

```
python scripts/content_script.py apply <course> --module 1 --confirmed --confirmed-by "<name>"    only after they said yes
python scripts/content_script.py discard <course> --module 1               they said no
```

Say who proposed and who said yes (2.49.2, F10): `propose --proposed-by "<who>"` (the operator in chat, or the agent
that worked the change out) and `apply --confirmed-by "<the operator's name>"`. The log row keeps both
(`[proposed by Claude (agent); confirmed by Aleksis]`); a Word or PDF read is "the operator (their Word file)". Left
out, a name is "not stated" — the log never claims the words were the operator's when nobody said so.

`apply` changes the script (and stops, exit 1, if the screens or a script field changed since the list was
made), logs every change in `FEEDBACK_LOG.md` (`3 · M01 · q06`, or `3 · M01 · script`), keeps the old Word file in
`working_claude/script/old/`, and writes a fresh page and Word file. Comments are **instructions, not
edits**: `apply` does not act on them — propose what you would change for each, show it, and apply
that when the operator confirms.

What is read, and how reliably:

| In the Word file | How it is read |
|---|---|
| text typed in a box | exactly |
| tracked changes | as if accepted; the list says which box had tracked changes, and by whom |
| a Word comment | placed on the box it was attached to |
| a box deleted outright | reported — never guessed; ask the operator |
| text typed outside the boxes | reported — never guessed; ask where it belongs |
| **PDF** comments | page number and the screens on that page — approximate; needs the `pypdf` package, and without it the factory says so and asks for the comments in Word or the chat |

## 4 · Approval — the operator's "next"

```
python scripts/content_script.py approve <course> --module 1 --by "<name>"
```

Refused while a pending list waits or the script has problems. **Any change after approval makes it a
draft again.** Record the approval in `COURSE_STATE.md` (L32). `status` says where a module stands.

**Approval is the operator's own act — never an agent's, never relayed** (2.49.2, F24). `--by` is the
person who read the words and said "next", in their own session. An agent does not run `approve` on an
instruction passed on from another session, a note, a handoff file or an earlier message: the permission
system of Claude Code blocks it — correctly, since a relayed "approve" is not the operator's word — and the
factory has no switch around it, by design. So:

- **Unattended runs** (overnight, a module agent, a batch): build with `compile_module.py --draft` and stop
  at the draft. Say in the report which scripts wait for approval; never try to approve them.
- **The operator approves in their own session**, after reading the review page or the Word file:
  `content_script.py approve <course> --module N --by "<their name>"` (they may ask an agent in that
  same session to run it, having just said yes there). The compiler then builds the real module.
- A script whose approval an unattended run needs stays a draft; nothing downstream pretends otherwise
  (`check_script_match.py` fails a build from a draft).

**An old script re-approved** (2.49.2, F9). A script approved before 2.42.0 keeps its approval and its
ILO-map findings are only reported. After a change that does not touch Sub-ILO tags, the sources or the
screens — a picture, a word — `approve` does not hold it to those rules again (it says so; `propose` also
says which applies). A change to a `sub_ilo` tag or the sources, or a screen added or removed, checks them
in full; a new approval always does, and records it (`approved_checks`).

**The theory check runs on the script, before any HTML** (2.17.0, L36): a slide too thin to teach from,
notes too thin to explain from, a module whose words do not fill its minutes, a self-check after too
little theory or with too few questions, a question whose answer the trainee has not been taught yet,
and a task written onto its slide. A slide longer than the room can read from the screen is a note.
Its findings head the review page and the Word file, and block approval the same way as the text check.

**The pictures-and-tasks check runs on the script too** (2.18.0, L37, L38): a slide with no kind of
picture or no word of what it shows, a long module where nothing moves, too few kinds of picture, a task
set answered only one way, too much "choose one", no hands-on question. The review page draws each
slide's picture area, lists the kinds and ways of answering, and lists what Novikontas or outside help
must provide — a photograph, a film, a 3D scan.

**The text check runs on the script, before any HTML** (2.16.1). `render` puts the same four rules
the finished slides get (`scripts/check_slide_text.py`, L22) over every screen: internal abbreviations,
an IMO model course cited as a source, version control on the opening slide, and the factory's own
markers. What the trainee sees — titles, slide text, questions, answers, feedback — is checked as a
course-facing page; the instructor notes and the planned-picture note are instructor-only, so a model
course there is a note, never a failure. The findings are at the top of the review page and the Word
file. `approve` is refused while a must-fix finding stands: fix it in the script (propose → confirm →
apply), or, if the operator has read it and wants the words as they are (L26), approve with
`--despite-findings` — the findings are recorded with the approval.

## 5 · Building from it, and proving it

**The deck is compiled, not typed** (2.25.0): `compile/GUIDE.md`. The marks below are what the compiler
writes; they are listed here for a module still built by hand.

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
