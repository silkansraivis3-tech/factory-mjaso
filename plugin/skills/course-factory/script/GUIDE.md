# Stage 3 — the module content script, word for word (L29)

Read this lane when a module's words are written, corrected or approved. **Nothing is built in HTML
until the operator has approved the script.** One script per module, plus one for the final
assessment (`--module final`). Everything is done with `scripts/content_script.py`; the check that the
built module obeys it is `scripts/check_script_match.py`.

## 1 · Write the script

`<course>/_factory/script/M01.json` — every screen **in the order the trainee meets it**. Each
self-check and each module-check question is **its own screen**, where it will appear.

```json
{"module": 1, "title": "<module title, course language>", "course_language": "English",
 "operator_language": "lv", "status": "draft",
 "operator_facts": [{"fact": "<what the operator said>", "where": "s03", "said": "2026-10-01"}],
 "screens": [
  {"id": "s01", "kind": "slide", "title": "…", "text": "line one\nline two",
   "visual": "<the picture planned, and where it comes from>", "notes": "<instructor only>", "minutes": 3},
  {"id": "q01", "kind": "self-check", "question": "…", "options": ["…", "…", "…"], "correct": "A",
   "feedback": "<what the trainee sees after answering>", "mechanic": "tap to choose"},
  {"id": "m01", "kind": "module-check", "question": "…", "options": ["…", "…"], "correct": "B",
   "feedback": "…", "mechanic": "tap to choose", "graded": false}]}
```

- `text` is the **exact visible words** of the slide, not a description of them. One line per line.
- Course text (titles, text, questions, answers, feedback) is in COURSE_LANGUAGE; the notes on the
  page and in the Word file around it are in the operator's language.
- Kinds: `slide`, `self-check`, `module-check`, `final`, `activity`. Module checks are never graded
  (L27) and come at the end of the module; a final-assessment script holds `final` questions.
- Every fact the operator stated is listed once, at the top of the review — from `operator_facts`
  and from `FEEDBACK_LOG.md` rows marked *operator-stated* for this module.
- NEW_ENTRANT or EXPERIENCED changes how much is explained and how (`knowledge/course-type.json`).

## 2 · Show it to the operator

```
python scripts/content_script.py render <course> --module 1
```

writes `review/M01_SCRIPT_REVIEW.html` (opens with a double-click, prints to PDF) and
`review/M01_SCRIPT.docx` — **the operator's copy is the Word file** (owner, 2026-09-30). Every
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
`_factory/script/old/`, and writes a fresh page and Word file. Comments are **instructions, not
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
