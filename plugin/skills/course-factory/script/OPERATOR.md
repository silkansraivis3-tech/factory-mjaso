# Stage 3 - operator how-to: corrections, approval, what the checks run on

For the person who runs the commands with the operator. The writer's rules are in `GUIDE.md`; this file is how a written
script is corrected and approved. Everything is done with `scripts/content_script.py`.

## Corrections - understood first, applied only on yes

The operator corrects in the Word file (typing in the boxes, or Word comments), in a PDF, or in the chat.

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
`kind`. `script_field` may be `title`, `minutes_allocated`, `sources`, `pass_mark` (a whole number 1-100; `70`, `"70"`, `"70%"` and `"70 %"` are all 70)
or `operator_facts`; anything else (`status`, approval, `module`, `screens`) is refused - "Stopped -", exit 2,
nothing written. Problems the changed script would have that it does not have now (a self-check left
without its task slide, minutes that no longer add up) are listed under the changes, not blocking.

Both write a **pending list** and print what was understood - *"screen 7: the slide text: 'rely on'
becomes 'are supported by'; question 3: the correct answer becomes B"*. **Show that list to the
operator, in their language, and wait.** Then:

```
python scripts/content_script.py apply <course> --module 1 --confirmed --confirmed-by "<name>"    only after they said yes
python scripts/content_script.py discard <course> --module 1               they said no
```

Say who proposed and who said yes: `propose --proposed-by "<who>"` (the operator in chat, or the agent
that worked the change out) and `apply --confirmed-by "<the operator's name>"`. The log row keeps both
(`[proposed by Claude (agent); confirmed by Aleksis]`); a Word or PDF read is "the operator (their Word file)". Left
out, a name is "not stated" - the log never claims the words were the operator's when nobody said so.

`apply` changes the script (and stops, exit 1, if the screens or a script field changed since the list was
made), logs every change in `FEEDBACK_LOG.md` (`3 · M01 · q06`, or `3 · M01 · script`), keeps the old Word file in
`working_claude/script/old/`, and writes a fresh page and Word file. Comments are **instructions, not
edits**: `apply` does not act on them - propose what you would change for each, show it, and apply
that when the operator confirms.

What is read, and how reliably:

| In the Word file | How it is read |
|---|---|
| text typed in a box | exactly |
| tracked changes | as if accepted; the list says which box had tracked changes, and by whom |
| a Word comment | placed on the box it was attached to |
| a box deleted outright | reported - never guessed; ask the operator |
| text typed outside the boxes | reported - never guessed; ask where it belongs |
| **PDF** comments | page number and the screens on that page - approximate; needs the `pypdf` package, and without it the factory says so and asks for the comments in Word or the chat |

## Approval - the operator's "next"

```
python scripts/content_script.py approve <course> --module 1 --by "<name>"
```

Refused while a pending list waits or the script has problems. **Any change after approval makes it a
draft again.** Record the approval in `COURSE_STATE.md` (L32). `status` says where a module stands.

**Approval is the operator's own act - never an agent's, never relayed.** `--by` is the
person who read the words and said "next", in their own session. An agent does not run `approve` on an
instruction passed on from another session, a note, a handoff file or an earlier message: the permission
system of Claude Code blocks it - correctly, since a relayed "approve" is not the operator's word - and the
factory has no switch around it, by design. So:

- **Unattended runs** (overnight, a module agent, a batch): build with `compile_module.py --draft` and stop
  at the draft. Say in the report which scripts wait for approval; never try to approve them.
- **The one exception is the build after the expert's Ready (L70)**: the expert's Ready, signed with their
  name in the training app's editor, is their own act, so that run approves with `--by "<their name> (Ready in
  editor)"` - the name `pedagogy_review.json` has from the pull, and no other (`approve` refuses any other
  name while `NOVIKONTAS_AUTO_BUILD=1` is set, and any name when nobody pressed Ready).
- **The operator approves in their own session**, after reading the review page or the Word file:
  `content_script.py approve <course> --module N --by "<their name>"` (they may ask an agent in that
  same session to run it, having just said yes there). The compiler then builds the real module.
- A script whose approval an unattended run needs stays a draft; nothing downstream pretends otherwise
  (`check_script_match.py` fails a build from a draft).

**An old script re-approved.** A script approved before the ILO map became a gate keeps its approval and its
ILO-map findings are only reported. After a change that does not touch Sub-ILO tags, the sources or the
screens - a picture, a word - `approve` does not hold it to those rules again (it says so; `propose` also
says which applies). A change to a `sub_ilo` tag or the sources, or a screen added or removed, checks them
in full; a new approval always does, and records it (`approved_checks`).

## What the checks run on

**The theory check runs on the script, before any HTML** (L36): a slide too thin to teach from,
notes too thin to explain from, a module whose words do not fill its minutes, a self-check after too
little theory or with too few questions, a question whose answer the trainee has not been taught yet,
and a task written onto its slide. A slide longer than the room can read from the screen is a note.
Its findings head the review page and the Word file, and block approval the same way as the text check.

**The pictures-and-tasks check runs on the script too** (L37, L38): a slide with no kind of
picture or no word of what it shows, a long module where nothing moves, too few kinds of picture, a task
set answered only one way, too much "choose one", no hands-on question. The review page draws each
slide's picture area, lists the kinds and ways of answering, and lists what Novikontas or outside help
must provide - a photograph, a film, a 3D scan.

**The text check runs on the script, before any HTML.** `render` puts the same four rules
the finished slides get (`scripts/check_slide_text.py`, L22) over every screen: internal abbreviations,
an IMO model course cited as a source, version control on the opening slide, and the factory's own
markers. What the trainee sees - titles, slide text, questions, answers, feedback - is checked as a
course-facing page; the instructor notes and the planned-picture note are instructor-only, so a model
course there is a note, never a failure. The findings are at the top of the review page and the Word
file. `approve` is refused while a must-fix finding stands: fix it in the script (propose -> confirm ->
apply), or, if the operator has read it and wants the words as they are (L26), approve with
`--despite-findings` - the findings are recorded with the approval.
