---
name: course-task-ux
description: >
  Apply whenever building, converting or reviewing an interactive TRAINEE TASK screen for a
  course delivered on a tablet — a self-check, a scored module check, tap-to-locate,
  sequencing, matching, a scenario decision, or a simulator reporting task. The locked task
  UX/UI standard: what a task screen may contain, how a trainee answers, how navigation,
  typed input and completion must behave, and what makes a task gradeable without a human
  reading prose. Trigger on "task page", "task card", "module check", "worksheet", "trainee
  task", "tablet task", "the keyboard won't close", or any request to make course tasks
  tablet-friendly, intuitive, or consistent across modules. Course-agnostic. Task screens
  only — not the module page or step runner (course-module-ux), not the deck, not the
  handout, never what a module teaches or assesses.
---

# Course task UX — the standard

**v2 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Ruled by a course owner across 2026-09-01/03 while reviewing a tablet build of 32 task
screens across eight modules. The owner quotes in this file are the evidence — they are why
each rule exists and why it is not negotiable on style grounds. They are quoted from a
previous course; **none of them are about your course's content.**

## The delivery target is a parameter, not a fact

Everything measurable below was ruled for:

> **Android tablet, 800 × 1280 portrait, offline, in a WebView, operated by a trainee's
> finger. Plain HTML/CSS/ES5. No build step, no frameworks, no network.**

A different programme on a different device **re-measures the floor** (§11) rather than
assuming these numbers. What does not change with the device: choosing over typing (§2), a
route back from every route out (§3), a way out of the keyboard (§5), an explicit completion
state (§9), and no record asking for a number the screen never showed (§10).

## What this skill owns, and what it does not

| Read when | |
|---|---|
| **always** | this file — the standard. Every mode reads it |
| a task has a text field | `references/typed-input.md` |
| before signing off any task page | `references/verify.md` + `scripts/` |
| writing the handover notes | `templates/task-notes.md` |

Deliberately **outside** this bundle. Point at these; never copy from them, because a copy
goes stale silently the moment the original is revised:

| Not here | Lives in |
|---|---|
| The one-page module architecture, START HERE, the step runner, the instructor run script, the deck measurement discipline | **`course-module-ux`** |
| Deck templates, House Rules, copy budgets, slide roles | `novikontas-presentations` |
| Exercise design, answer keys, rubrics, ILO coverage — **what a task assesses** | `novikontas-practical-exercises`, `novikontas-exercise-description-trainee` / `-instructor` |
| Written tests on paper | `novikontas-written-tests` |
| The module's visual token set a task page draws from — palette, radius, shadow, semantic correct/wrong/hazard colour | **`course-module-ui`** |
| Brand colour, typography, logo | `novikontas-brandbook` |
| Applied pedagogy — ILO wording, task depth, sequencing | `novikontas-pedagogy-toolkit` |

This skill governs **the screen**. It never decides what a task assesses, and it never
touches course content — see §14.

## What a new programme must supply

This bundle is empty of course material by design. A new programme brings:

1. **Its task content** — the questions, options, explanations, photographs and their
   licences. From the exercise skills above, not from here.
2. **Its answer keys** — which option is right and *why*, because the reasoning is rendered
   on the task screen (§2) rather than on a deck slide.
3. **A manifest of its tasks** — one row per task, which is also the approval gate below.
4. **Its own measured floor** if the device is not an 800 × 1280 portrait tablet.

## The gate — before writing any HTML

Building task screens is the expensive step. Editing a row of a table is free; re-editing 32
built pages is not, and a wrong answer mechanic is not a cosmetic fix. So present this table
and get approval before writing markup:

| # | Task | Answer mechanic (§2) | Parts | Typed input? | Numbers a record asks for (§10) | Engines |
|---|---|---|---|---|---|---|

The **Numbers** column is the one people skip and the one that has already caused a defect.
Fill it from the record sheet, not from the task.

---

## 1 · What a task screen must NOT have

**No header block.** No course name, no module number, no task code, no "in-class activity"
label, no time estimate, no ILO or Sub-ILO code, no scored-item count.

> "remove header completely, GASxxx Gas Basic Module 1 In Class Activity its not needed, how
> much time it is also not needed, because on screen trainee will see that"

The trainee arrives from a card that already showed the title and the description, and the
instructor's screen carries the briefing. The task begins with the task. Keep only the
injected back-link.

**No handout advertising.** The handout has its own route on the tablet's first screen. A
task list must not carry a handout card, and a task screen is not a shop window for it. A
single contextual deep link inside a task ("the annotated permit is §3") is acceptable where
it genuinely helps mid-task; a "the handout is yours" card is not.

**No printed-worksheet thinking.** No "read this page, then go to another page, then type
your answer in". No group-work tasks unless the delivery actually has a system for grouping
trainees — the reference build did not.

**No fake or duplicated furniture.** No mock-up of the app's own UI. No "SCREEN 1 OF 4"
counters that describe the document rather than help the trainee.

---

## 2 · How a trainee answers

**Self-checks and module checks: choosing, not writing.**

> "in self check or assesments, try to make tasks without 'write the answer', becuase its
> self check, its difficult to grade what trainee typed himself, better let him choose
> answers, or find them, but not type them"

Allowed answer mechanics:

- **tap to choose** one option from a set
- **tap to locate** a thing on a photograph or drawing (§6)
- **order / sequence** by dragging or by arrows
- **match** pairs
- **choose-and-justify** — pick the action, then pick the reason from a set (both must be
  right; this is how reasoning gets assessed without free text)

**Free typing is allowed in exactly one place:** a *simulator or field reporting* task, where
reporting what you did or saw is the point of the exercise. Nowhere else. If it is allowed,
§5 becomes mandatory.

**One Submit per part.** A part is submitted on its own. Correct items lock and grey out with
an explanation of *why* they are correct; wrong items get a hint and another attempt. The
reasoning lives in the task, which is why the deck needs no answers slide.

---

## 3 · Navigation — the rules broken most often

**Every route out has a route back.** If a task opens a second page, that page returns to the
exact page it came from. A trainee must never have to go up to the module list and re-enter
the task to get back to where they were.

> "if i open the four triggers, i cannot basically and safely come back to shutdown page, i
> need to go to module 2 tasks and open task cards again, its bad"

**Never end a task with a row of unexplained buttons.** Two buttons offering different next
things, with no statement of which is which, is worse than one. In particular a task must not
offer to jump to a different numbered task.

> "there is two buttons : The four triggers and Open GAS203, WHY?"

**The task list is numbered by position.** Task cards show **1, 2, 3, 4** — not a category
letter or a course code. The trainee navigates by "where is task 2", not by task code.
Reference-material cards keep their own glyph, because they are not a numbered step.

**Returning must not re-ask for the session code, and must not flash the start screen.** Any
page linking back into the shell carries a route hash, and the shell pins the resumed state
with a class rather than racing whatever the start-screen animation does next.

---

## 4 · Understandable without a wall of text

> "please fix that but not with text, like DO THIS THEN THIS, maybe try to implement
> navigation and explanation inside ux ui, so it would be intuitive and understandable ...
> that doesnt means dont use text as navigation or explanation ... but do it so even i
> understand what to do"

The test: **someone who has never seen the task can tell what to do from the screen alone.**
Text is allowed; text as the *only* mechanism is not.

- **State visible at all times.** Which part am I in, how many are left, what have I got
  right. A persistent bar, not a paragraph.
- **One live action.** At any moment exactly one control is obviously the thing to press.
  Everything else is quieter.
- **The answer's shape is visible before the answer.** Six slots for six findings tells the
  trainee what "done" looks like.
- **Progressive disclosure.** Part 2 is not on screen while Part 1 is unfinished.
- **Show, then ask.** If the trainee must read a document to answer, the document and the
  question are on the same screen — not one page apart.

---

## 5 · Typed input must have a way out

Wherever §2 permits a text field, the soft keyboard has to be dismissible **from the screen**.

> "when i try to type my name in module2 task cards, i cannot basically and safely come back"

A WebView raises the keyboard when a field takes focus and lowers it when that field loses
focus. If nothing on the page ever takes focus away, the keyboard sits over the bottom third
with no way back. The device Back button works, but a trainee should not have to know that,
and on a kiosk tablet Back may be bound elsewhere. One page in the reference build had 99
fields and was unusable.

**Three routes out, because any one of them can be unavailable:**

1. `enterkeyhint="done"` on every single-line input, so the keyboard's own action key reads
   Done rather than a next-field arrow;
2. **Enter blurs a single-line input** — textareas are exempt, because Enter is a newline
   there and that is the point of a textarea;
3. a **"Done ✓" pill**, shown only while a field has focus, at least 44 × 44, positioned so
   it never covers the field it dismisses. This is the only one of the three that cannot be
   defeated by a WebView quirk, so it is the one that must never be dropped.

This is engine-level, not per-page: bundle it once and load it. Read
**`references/typed-input.md`** for the wiring and the failure modes, and load
`assets/kbd_escape.js` + `assets/kbd_escape.css`.

---

## The look of a task page is not this skill's to invent

Load, in this order:

```html
<link rel="stylesheet" href="../assets/gb_tokens.css">   <!-- course-module-ui -->
<link rel="stylesheet" href="../assets/gb_page.css">     <!-- course-module-ui: the page frame -->
<link rel="stylesheet" href="../assets/gb_task.css">     <!-- here: the task controls -->
```

`gb_task.css` owns the state bar, the question stem, the 52 px option, the why panel and the
in-task figure. It owns **nothing else** — a task page is a document page with a task on it.

Every task page also carries `<a class="gbt-topback" href="…">`, which is what the Android
hardware Back button clicks. Without it, Back exits the app.

**Do not copy these rules into a page's own `<style>`.** ETPB3's task pages each kept a private
copy written against the retired ETPA1 dialect — `var(--okbg)`, `var(--ok)`. When the dialect was
removed those names stopped resolving, and an unresolvable custom property voids the whole
declaration: the correct answer and the wrong answer both rendered with a transparent ground and a
black border. Every static check passed. `course-module-ui/scripts/audit_ui.py` now catches it.

---

## 6 · Tap-to-locate tasks

- **Cap the taps at the number asked for.** "Find 6 hazards" accepts 6 taps, not 20.
- **Tapping an existing mark removes it** — that is the undo. Provide **Erase all** as well
  if per-mark removal is fiddly.
- **Hints may be subtle and brief.** A short, low-opacity glint at the places worth looking,
  not permanent circles that give the answer away.
- **Never number the targets in a helper list when the targets are asked for in that
  order** — it turns knowledge into counting. Verified failure mode: a six-zone task whose
  zones sat in exactly the asked order, with 1–6 printed on the pins.
- **A picture must not sit next to the question it answers.** Put the recognisable photograph
  in the *feedback*, not beside the data the trainee is meant to read.

---

## 7 · Real photographs

Prefer a real photograph to a drawing. Draw only what no photograph can show (inside a hull,
inside insulation, below deck) and **say on the page that it is a drawing**.

- Every photograph needs its **licence and credit on the page** — a legal condition, not
  decoration.
- **Open the file and look at it** before using it, and read its own recorded description.
- **A caption may only claim what the photograph evidences.** If the source says the picture
  is of oil tankers, the caption says oil tankers — even when it is illustrating something
  else.
- Photographs a trainee is asked to identify from should be **tappable to full size**.

---

## 8 · Two-stage tap, and close buttons

Where a card opens and its picture can also enlarge:

1. **First tap opens the card and nothing else** — including a tap on the picture.
2. **Only an open card lets its picture go full screen.**
3. **Always a close button**, at least 48 × 48, on both the opened card and the full-screen
   view.
4. **The tap hint never sits on top of content.** A closed card says "tap to open" in normal
   flow beneath the picture; a badge over the picture is acceptable only on the opened card,
   where the picture is large.

---

## 9 · Completion is explicit, and the same everywhere

Every task ends the same way: a state that says **the part is finished** and **what happens
next**. Without it a trainee finishes, sees nothing change, and either sits unsure or keeps
tapping a finished task.

Drive it from **one shared engine**, not per-page markup — 32 pages hand-rolling an ending
produced 32 slightly different endings. Load `assets/task_complete.js` +
`assets/task_complete.css` and call it from the task's own finish handler.

- **A panel, not an `alert()`**, and dismissible: the reason for every answer is on the page
  behind it, and reading those reasons is the point.
- **Quiet.** A self-check and a recorded check differ by one line of ordinary type. The panel
  never says "PASSED".
  > "no need to type REMEMBER, ITS ONLY SELF TEST, maybe small notice but not like contrast info"
- **Never animate it into visibility.** Its resting CSS state must already be visible. In an
  offline WebView a stalled compositor leaves an animation at its `from` state, and the panel
  is present, correct, and invisible — that was measured at opacity 0 twice before the cause
  was found. Ask of any motion: *what does this look like frozen?* A 10px transform is safe; a
  fade is not.

---

## 10 · Never ask a trainee to record a number the screen does not show

A task computed a total, declared the variable, and never rendered it — while the record
sheet asked the instructor for "the score their tablet showed". Arithmetically correct,
operationally impossible.

**Every number any record asks for must be visible on the trainee's screen at the moment it
is asked for.** Not derivable, not in a variable, not in the console: rendered.

Check it in both directions, and check it against the record sheet rather than the task:

- for each number the record names → find the element that paints it;
- for each total the task computes → find where it is written to the DOM.

`scripts/check_task_pages.py` flags computed-and-never-painted totals as candidates. It is a
heuristic; the record sheet is the authority.

---

## 11 · Measurable floor — verify, do not assume

At the target viewport (**800 × 1280 portrait** for the reference build), on every task
screen:

| | Requirement |
|---|---|
| Tap targets | **≥ 44 × 44 CSS px**, no exceptions |
| Text size | **≥ 12.5 px** for anything a trainee reads |
| Contrast | **≥ 4.5 : 1** (3 : 1 for large text) against the *resolved* background |
| Horizontal scroll | **none** — wide tables and drawings scroll inside their own container |
| Overlap | **none** — no text over text, nothing escaping its container |
| Console | **no errors**; every widget initialises |
| Network | **no requests** beyond an already-accepted font link |
| Keyboard | if there is a text field, all three routes out of §5 present |

**The browser measurement is the authority. Every static check is a pre-filter.** A static
finding is a question to take to the page, never a defect to fix on sight.

**A clean report from an unverified probe is worse than no report.** The procedure, the
in-page probe, and the traps that have produced false results — a pane laying out at 0 × 0,
SVG text whose declared size is not its painted size, stale stylesheets, `clamp()` not
recomputing — are in **`references/verify.md`**. Read it before reporting any measurement.

### 11.1 · A responsive size has three dials. Read the one that binds

`clamp(MIN, COEFFICIENT, CEILING)` resolves to exactly one of the three at any given
viewport, and **only the resolved value means anything.** Reading a single dial makes you
wrong about the other two, and both directions have actually happened:

- **The coefficient can paint under the floor whatever the minimum says.** At a 768 px
  viewport dimension `1vmin` is 7.68 px, so anything under about **1.63vmin** is sub-floor no
  matter how healthy its minimum looks. One deck carried 65 such instances.
- **The ceiling can bind so the coefficient never engages at all.** Elsewhere, 43 rules were
  capped under 20 px by their third argument.
- **And the minimum very often never applies.** `clamp(11px, 1.6vw, 14px)` at 800 px wide
  resolves to `1.6 × 8 = 12.8 px` — the coefficient binds, the 11 px minimum is unreachable,
  and the rule passes.

So the check is: **compute `MIN`, `COEFFICIENT × viewport` and `CEILING` at the target
viewport, take whichever binds, and judge only that.** v1 of this skill said "at 800 px wide,
`1.5vw = 12px`: it is the clamp minimum that a portrait tablet gets" — true at exactly 1.5vw
and misleading everywhere else. Believing it produced **12 false findings on one real
stylesheet, every one of which measured fine in the browser.**

`scripts/check_task_pages.py --only floor` does this resolution and names the binding dial in
every finding. `--viewport WxH` defaults to `800x1280`; a different device passes its own,
because the floor is re-measured, not inherited. Anything the resolver cannot evaluate
statically — `em`, `%`, `calc()`, `var()` — it reports **not at all** rather than guessing,
which is the right trade when the browser is the authority.

---

## 12 · After any scripted or templated edit, load the page and read the console

A generated object literal was missing one comma before a property. The console read
`SyntaxError: Unexpected identifier`, the whole inline script failed to parse, and **every
button on two task pages silently did nothing** — while the pages still looked perfect.
Separately, a comment replacement left the old comment's tail as bare JavaScript and killed
another script the same way.

An inline script is all-or-nothing. One bad token anywhere in it disables every control the
page has, with no visual symptom whatsoever. So:

**Any edit made by a script, a template, a regex or a bulk find-and-replace is not finished
until the page has been loaded and the console read.** Not "the diff looks right".

`node --check` on the extracted inline scripts is the fast check, and
`scripts/check_task_pages.py` runs it for you — but **`node` is frequently not installed** on
these machines (it is not, on the reference one). When it is absent the script says so and
exits non-zero for that check, and the **browser console becomes the only syntax check
available**. It is not optional in that case; it is the check.

---

## 13 · Dead markup, and specs that outrun the code

Dead markup accumulates and then misleads the next person into preserving it.

**Sweep, with `scripts/check_task_pages.py`:**

- an **id or `data-` hook referenced by no script and no stylesheet is deleted**. Two task
  pages carried `<span id="gb-home">` / `<span id="gb-deck">` that nothing read;
- a **class styled in stylesheets but present in no markup in scope is deleted from those
  stylesheets**. One class was styled in seven stylesheets and existed in exactly one page's
  markup — dead in six;
- and the mirror of that, `--only states`: **a class the ENGINE adds at run time that no
  stylesheet styles**. The states that decide whether a task teaches anything — chosen,
  right, wrong, explanation revealed — are set the instant a trainee taps, so they appear in
  no markup and every other check here is blind to them. The ETPA4 pilot shipped a page whose
  sheet styled `.ok`/`.no` under an engine that sets `right`/`wrong`: a right answer looked
  exactly like a wrong one, and syntax, deadmarkup, numbers, floor and kbd were all green.

  The answer states are `sel`, `right`/`ok`, `wrong`/`no`, `dim`, with `why.good`/`why.bad`
  for the explanation and `.sub` for the confirm button — `assets/gb_task.css` carries them
  all. Read the engine before styling a name: `.sub` reads like a subtitle and is a
  full-width 56px button, and `.part2` reads like a divider and is `display:none` until the
  engine reveals it. Styling that one as visible puts the answer on screen before the
  trainee has predicted anything.

And the direction that matters more:

> **A rule stated in a skill or a spec that the reference implementation does not actually
> follow is wrong in the skill, not missing from the code.**

That happened: a spec listed an element as mandatory that the reference implementation had
never had. The spec was the defect. When code and spec disagree, find out which one shipped
and worked before changing either.

---

## 14 · Shared engines drift, and generated builds overwrite

The engines are usually **per-module copies** — `kbd_escape.*`, `task_complete.*`, a step
engine, a pin engine, a task stylesheet. A fix to one is a fix to none:

- **apply it to every module in scope, or record the drift deliberately** in the notes
  (§Markers) as a `PROVISIONAL` with the reason;
- a **generated single-file build overwrites hand edits**. Edit the authored sources and
  re-run the build. Patching the output is a change that disappears at the next build and
  takes a day to diagnose.

**Never change course content while doing UX work** — wording of questions, answers,
explanations, values, units, terminology or source citations. Maritime and other domain terms
stay exactly as written even when they look like typos. If a UX fix seems to need a content
change, stop and report it as a `[VERIFY: …]` line rather than making it.

---

## Honesty markers, and the notes file

Never fill a gap plausibly. Use exactly these four, and land every one of them in the notes
file so nothing is used and never reported:

| Marker | Means |
|---|---|
| `UNKNOWN` | Asked the owner, the owner did not know. Recorded with the fact that it was asked |
| `PLACEHOLDER` | Structure is right, real content is missing |
| `PROVISIONAL` | Built, but depends on something unapproved — an unapproved answer key, a deliberate cross-module drift |
| `[VERIFY: <what to check>]` | Asserted from a source this skill could not confirm — a licence, a value, a record-sheet field. Always carries its payload |

Never invent a photograph's licence or credit, a regulatory reference, or an answer key.

Write **`templates/task-notes.md`** during the run, not afterwards, and finish it with the
feedback section on this skill — that section is the only channel through which real delivery
reaches this standard. Read it at the next revision.


---

## 15 · Every number a screen states must match the page *(added 2026-09-07)*

A projected screen told a room:

> **Eight questions.** On your own. · **One attempt.** Read it before you answer.

The page it pointed at had **ten** questions, computed its pass mark as
`need = ceil(0.75 * Q.length)` = **8 of 10**, and carried a **"Clear and try again"** button plus
prose inviting a retake. So "eight" was the *pass mark* read as the question count, and "one
attempt" was the opposite of what the page does. An instructor reading that screen aloud tells
the room two things their tablets contradict.

It got worse downstream. The same stale figure had been copied into the assessor's score sheet in
four places, including the borderline instruction *"a NOT PASSED on 6 or more means the element
rule failed"* — which, once the check grew to ten questions, would have **overturned a correct
fail**. And into the instructor terminal's own reference and record, so the instructor's tablet
disagreed with the trainee's.

**The rule.** Any number a deck, plan, score sheet or reference states about a task — question
count, pass mark, attempts, minutes — is **derived from the task page or not stated at all**.
When you must state it in prose:

- state it as the proportion the standard actually is, with the count after it
  ("75 % of the check, currently 8 of 10"), so the next added question does not create a lie;
- grep the number across **every** tree before believing it is only in one place. It took six
  files to correct one figure;
- and check the attempt policy the same way. A "try again" button is the page's answer to that
  question; prose is not.

Cheapest possible check, worth running on every course: for each task page, count its question
array, read its pass computation, list its buttons — then grep every artefact that names that
task and compare.

## 16 · Nothing is useless until you grep for what depends on it *(added 2026-09-07)*

Asked to list every control and text that might be useless, I produced four headline findings.
**Three were wrong**, each in the same way: I judged the control by looking at the control, not by
looking for what depends on it.

- **"31 timer widgets = 62 Start/Reset buttons, the biggest useless-button item."** Wrong. The
  generated instructor step-by-step and six deck cues say *"Press Start when the room is on the
  check and let it run."* They are part of the documented procedure the instructor reads on their
  own tablet.
- **"7 Print buttons on a tablet with no printer."** Wrong twice. Every one is on a hand-out
  *document* — briefing sheets, marking criteria, the paper version of the check, which even
  carries an `@media print` stylesheet. And Android's print dialog offers *Save as PDF*, so "no
  printer" was not the right test.
- **"67 dead `<span id="gb-home">` controls."** Wrong. The run engine reads the `href` off those
  anchors and does `if (!deck && !home) return;` — so an hrefless span is how a page **declares it
  has no way back**, suppressing the navigation bar. Load-bearing markup that looks like litter in
  a grep.
- The one that was right: 73 "not yet approved training material" footers, which nothing
  referenced and the owner had already asked to have removed.

**Before listing anything as useless:**

1. grep the id, class, label and filename across **both tablet trees, the course tree and every
   generated script**;
2. read the consuming code's **null branch** — graceful degradation often means the "dead" thing
   is a deliberate switch;
3. ask whether a **planned** system needs the data. Unused today is not useless: 36 per-question
   explanation strings sat unread in an assessment and are exactly what the instructor-side result
   view will render;
4. then report — and say what you checked, so the owner can overrule the reasoning rather than
   the conclusion.
