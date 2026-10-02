# Stage 3 — the module content script, word for word (L29)

Read this lane when a module's words are written, corrected or approved. **Nothing is built in HTML
until the operator has approved the script.** One script per module, plus one for the final
assessment (`--module final`). Everything is done with `scripts/content_script.py`; the check that the
built module obeys it is `scripts/check_script_match.py`.

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
 "screens": [
  {"id": "s01", "kind": "slide", "title": "…", "text": "line one\nline two",
   "visual": "<the picture planned, and where it comes from>", "notes": "<instructor only>", "minutes": 5},
  {"id": "t01", "kind": "task-slide", "opens": "SC1", "title": "Self-check 1 - …",
   "text": "<only: a task starts now, and what it is about>", "notes": "…", "minutes": 4},
  {"id": "q01", "kind": "self-check", "set": "SC1", "question": "…", "options": ["…", "…", "…"], "correct": "A",
   "feedback": "<what the trainee sees after answering>", "mechanic": "tap to choose"},
  {"id": "t02", "kind": "task-slide", "opens": "MC", "title": "Module check - …", "text": "…", "notes": "…", "minutes": 6},
  {"id": "m01", "kind": "module-check", "set": "MC", "question": "…", "options": ["…", "…"], "correct": "B",
   "feedback": "…", "mechanic": "tap to choose", "graded": false}]}
```

- `text` is the **exact visible words** of the slide, not a description of them. One line per line.
- **Enough theory (L36, `knowledge/theory-rules.json`).** A slide carries the teaching itself - the facts,
  numbers, names and reasons its Sub-ILO needs - not a headline (50-150 words, title included); the notes
  carry what the instructor explains, adds or asks beyond it (30 words or more); the module's slides and
  notes together fill its theory minutes (40 words a minute or more). A self-check comes only after a
  block of new theory (10 min and 400 words since the last task), and every question's correct answer
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
  is animated; what has an inside is a cutaway or a 3D model; what must be recognised on board is a real
  photograph, a scan or a photo to take at Novikontas — never an AI picture (L33).
- `"from_old"` (optional, L41) — where in the old course the slide comes from and what changed: *"1. Liquefied Gas
  tankers.pptx, slides 37-40 - the photographs became a 3D model"*. Shown on the review page.
- `"visual"` — what it shows and why, in one or two sentences; `"layout"` — `split` (text left, picture
  right), `visual_wide` or `visual_full`.
- **No quota** (2.18.1): wherever a picture, an animation or a realistic 3D illustration can show what the slide
  teaches, put it in. A slide with none, a long module where nothing moves, few kinds of picture - these come
  back as suggestions, never blocks; nothing is added only for variety (L13).

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

Both write a **pending list** and print what was understood — *"screen 7: the slide text: 'rely on'
becomes 'are supported by'; question 3: the correct answer becomes B"*. **Show that list to the
operator, in their language, and wait.** Then:

```
python scripts/content_script.py apply <course> --module 1 --confirmed     only after they said yes
python scripts/content_script.py discard <course> --module 1               they said no
```

`apply` changes the script, logs every change in `FEEDBACK_LOG.md`, keeps the old Word file in
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
