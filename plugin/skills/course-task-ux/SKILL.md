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

> **Every reply to the operator** (L25): three parts as short points - **Done · Check now · Next** -
> in everyday words, for someone who knows nothing about IT. The full rule: `course-factory/SKILL.md`.

The rules here were ruled by a course owner while reviewing a tablet build of 32 task screens across eight modules.
The owner quotes that are the evidence — why each rule exists — are in `references/rulings-in-full.md`; they are
quoted from a previous course and **none of them are about your course's content.** "Not negotiable" means the
factory never relaxes them on its own; it never means refusing an operator's request (L26).

Design is the person's (L26): tell them the risk first, then record their choice with `design_choices.py add` (course-factory); it is never changed back.

## The delivery target is a parameter, not a fact

Everything measurable below was ruled for:

> **The trainee tablet: Android, landscape 1280 × 800 (1024 × 768 stated), offline, in a WebView, operated by a
> trainee's finger. Plain HTML/CSS/ES5. No build step, no frameworks, no network.** Tasks run only on the trainee's
> tablet (L35); `course-module-ux/measure/knowledge/floor.json` → viewports is the table of sizes.
>
> **L45:** the classroom system opens a task inside a frame - an Android WebView in landscape, about
> 1280 × 800, touch only. New task pages are built and measured for that. Each page reports its result once with
> `gb-task-done` (code, title, ok, total, items, head), listens for the classroom's `gb-timer`, offers no retry inside
> the classroom, and never shows the answers in its source - `course-factory/knowledge/classroom-system.json` →
> `task_page`.

A different programme on a different device **re-measures the floor** (§11) rather than
assuming these numbers. What does not change with the device: choosing over typing (§2), a
route back from every route out (§3), a way out of the keyboard (§5), an explicit completion
state (§9), and no record asking for a number the screen never showed (§10).

## What this skill owns, and what it does not

This file is the standard; every mode reads it. Also: `references/rulings-in-full.md` before relaxing or changing a
rule (same section numbers) · `references/typed-input.md` for a text field · `references/verify.md` + `scripts/`
before signing off a task page · `templates/task-notes.md` for the handover notes.

Not here, point at them: module page, step runner, run script → `course-module-ux` · deck templates, copy budgets →
`novikontas-presentations` · what a task assesses (exercises, answer keys, rubrics) → `novikontas-practical-exercises`
and the exercise-description skills · written tests → `novikontas-written-tests` · the look a task page draws from →
`course-module-ui` · brand → `novikontas-brandbook` · ILO wording, task depth → `novikontas-pedagogy-toolkit`.

This skill governs **the screen**. It never decides what a task assesses, and it never
touches course content — see §14.

## What a new programme must supply

This bundle is empty of course material by design. A new programme brings:

1. **Its task content** — the questions, options, explanations, photographs and their
   licences. From the exercise skills above, not from here.
2. **Its answer keys** — which option is right and *why*, because the reasoning is rendered
   on the task screen (§2) rather than on a deck slide.
3. **A manifest of its tasks** — one row per task, which is also the approval gate below.
4. **Its own measured floor** if the device is not the 1280 × 800 landscape tablet.

## The gate — before writing any HTML

Building task screens is the expensive step. Editing a row of a table is free; re-editing 32
built pages is not, and a wrong answer mechanic is not a cosmetic fix. So work out this table
before writing markup. When the tasks are compiled from an approved content script, the table is printed
for the record and the build goes on - no stop; wait for approval only for a hand-built set with no approved script:

| # | Task | Answer mechanic (§2) | Parts | Typed input? | Numbers a record asks for (§10) | Engines |
|---|---|---|---|---|---|---|

The **Numbers** column is the one people skip and the one that has already caused a defect.
Fill it from the record sheet, not from the task.

The words of every task — question, answers, correct answer, feedback, and the
mechanic — are approved by the operator in the module's content script first (`course-factory`
`script/GUIDE.md`, L29). This table then comes from the approved script; it is not a second
approval of the content. Every task page built from it carries `data-script` and
`data-script-field`, so `check_script_match.py` can prove the words are the approved ones.

---

> **The owner's rulings behind every section below — the quotes, the failures and the numbers —
> are in `references/rulings-in-full.md`, word for word, under the same section numbers.** Read a
> section in full before arguing with it, relaxing it or changing it.

## 0 · The trainee who has never held a tablet (L42) - this comes first

*"For tablet tasks I need tablet-friendly UI/UX, user-friendly as well, but max modern, max technology and max
understandable - so people even with zero tablet experience do the tasks, and they are excited."*

The test for every task screen: **someone who has never used a tablet does it without help, and enjoys it.** Both
halves count - a task that is clear but dull fails, and so does one that is impressive but confusing.

1. **A first try, before the first task.** The course's first task opens with a 20-second *"try the tablet"*
   screen - tap this, drag this here - with a friendly check mark. Not scored, never repeated.
   **Which group, before a set that differs per group.** When the script has `"groups"` and a set has a
   question for one group, its page opens on *Which group are you in?* - one big button per group (110 px high, the
   name in 28 px), nothing else to press, no typing, no timer. The tablet keeps the choice for the course, so later
   tasks open straight on their questions; a small label in the top bar names the group and, until the first Check,
   takes the trainee back to choose again. They see, are numbered and scored over their own questions.
2. **Only tap and drag.** Every drag also works as *tap the item, then tap where it goes*. Never double-tap,
   long-press, swipe-to-move-on or pinch as the only way; a 3D model has turn and zoom buttons as well as gestures.
3. **Show, don't tell.** The first time a kind of task appears, a short animated hand shows the gesture once, then
   goes. The screen itself shows what to do - the slots for the answer, the item that can be moved (it lifts slightly
   and has a grip), the one button that matters.
4. **Big, and one thing at a time.** Sizes are in §11. The Next / Check button is big and in the same place on every
   screen (bottom, full width). One question per screen (L35), plenty of space, nothing small to aim at.
5. **Alive, instant feedback.** Every touch answers within a tenth of a second: a press state, a soft snap when a
   dragged item lands, a calm shake and its brief reason on a wrong answer, a check mark and the reason on a right one. The last
   screen shows the trainee's own score as an animated ring - rewarding and professional, never childish.
   A tick means *you did this, and it is right*: with `"feedback": "now"` (§2b), when several answers are right and one was missed, the missed one is
   outlined in green and says **"Also right"** - never ticked as if it had been chosen (`gb_answer.js`).
6. **Modern and real.** Real equipment on the screen - 3D models that turn, real photographs, panels and gauges that
   look and behave like the ones on board; smooth motion between steps; the module's own look (`course-module-ui`).
   Nothing may look or feel like an old web form.
7. **Forgiving.** Nothing can be broken or lost: a wrong drag can be moved again, an answer can be changed until Check
   is pressed; the page shows no countdown of its own, and when the instructor sets the classroom timer (`gb-timer`) the page obeys it (§9a). The trainee is never stuck and never sees an error message.
8. **Fast and offline.** No loading spinners, nothing fetched (L6) - every picture, model and sound is in the pack.
9. **Proved, not assumed.** Step 6 checks every task type at tablet size in a browser; QA adds a *"never used a
   tablet"* walkthrough - a colleague doing every task in their own browser with no explanation (L39); the owner's
   real-tablet touch test comes at the end.

`course-factory/knowledge/media-and-tasks.json` → `trainee_tablet_experience` holds the same numbers for the scripts.

---

## 1 · What a task screen must NOT have

- **No header block** — no course name, module number, task code, "in-class activity" label,
  time estimate, ILO or Sub-ILO code, or scored-item count. The trainee arrives from a card that
  already showed the title. The task begins with the task; keep only the injected back-link.
- **No handout advertising.** A single contextual deep link inside a task is acceptable where it
  genuinely helps mid-task; a "the handout is yours" card is not.
- **No printed-worksheet thinking** — no "read this page, then go to another page, then type your
  answer in", and no group work outside the classroom's team-task system (§9a).
- **No fake or duplicated furniture** — no mock-up of the app's own UI, no "SCREEN 1 OF 4" counters.

---

## 2 · How a trainee answers

The task screens' layouts - where the question, its picture, the answers and the side cards go - are in
`course-module-ui/knowledge/blueprints.json` "tasks", with their live references in `design/task-templates` (the
twelve quick-check screens in `live/`, the richer-task demos in `engines/demo/tasks/` (three built as engines so far), both themes by `themes.py`).
Every compiled task page has that look: `assets/gb_task_look.css` loads last and gives each question's screen the white
or the Navy theme - the other one than the screen before, or the build sheet's `"theme"` - and changes no size, place
or typeface weight of `gb_answer.css`, so every fit and tap area stands. Each question names its picture (a static 3D
render or a photograph, build sheet `"figure"`); a screen without one is fine, and a picture that would give the answer away goes in the feedback (§6). The answers themselves can be
pictures (`"figures"`: a tile each to tap; on true or false, a picture behind each card), the places to put in order sit
on one rail, a match's names are joined to their places, and set the value has a knob a finger turns.

The richer tasks become ways of answering one at a time: each a template in `engines/` (the reference's logic, the course's
data in one JSON block, no right answer readable - only its key), built in its screen's theme (`scripts/engine_theme.py`)
and shown in a frame on its question's screen, the set page counting its report as the answer. Built so far: the deck
round (`deck_round`), dress for the job then check a buddy (`dress_for_job`), lay out the equipment (`lay_out`).

**Self-checks and module checks: choosing, not writing** (the ways to answer: `media-and-tasks.json` → `mechanics`).

> **L38:** as many ways of answering as possible, realistic and technical. The list of ways, how each answer is
> written and the variety floors are in `course-factory/knowledge/media-and-tasks.json`; the operator approves every
> task's words in the content script first.

**Typing is avoided; where typed input is unavoidable it must have a way out (§5).**

**One Check per part.** Until Check a trainee can change any answer; at Check the part locks. Inside the
classroom frame there is no second attempt - a wrong item says *Not right*, its brief reason, and that it is
taken up in the debrief (§2b). Outside the frame (revision) a retry is allowed. The reasoning lives in the task, which is why the deck needs no
answers slide.

### 2a · More, for the higher Bloom levels

*"Tablet interactive tasks - not only drag n drop, choose e.c., something completely different, interesting and
creative."* Still no typing, still tap and drag (drag always also tap-then-tap), still §0 first. The mechanics and
their answer formats are in `course-factory/knowledge/media-and-tasks.json`; every item the page shows carries
`data-script-field="answer"`, exactly the items `content_script.answer_items` lists, and the right ones carry their
`data-key` (`classroom-system.json` → `task_page.answer_keys`). How each looks and behaves on the tablet is in the
engine (`assets/gb_answer.js`, `gb_interact.js`) and `templates/interact/`; rules that hold for all of them: checking a
part in *find the fault* is free and never wrong; a wrong card in *build the plan* says why; *rebuild the incident*
is two parts (the order, then the stop point), each with its own Check; *fill the table* cells are 56 px or more, up
to 6 rows x 5 columns, and its keys are `gbKey(id, "row | column", value)`.

**Every mechanic in `course-factory/knowledge/media-and-tasks.json` is compiled:** `compile/scripts/task_pages.py` builds each from the approved
script and the one shared engine, `assets/gb_answer.js` + `gb_answer.css`, grades it - a question is one or more parts,
each with its own Check (a scenario's steps; the incident's order, then its stop point). Task pages are compiled from
the approved script; a page the compiler cannot express is hand-made on the same engine and passes the same checks.

None of them hides information the trainee needs to answer: the readings in *find the fault* are one tap away and
stay turned over; a wrong answer is never an error message - it is *Not right*, its brief reason and the debrief (§2b, L42).

### 2b · Part A and Part B, and the interactive types

*"More interesting / modern / technology self checks, so self checks become practical learning as well ... first the
trainee checks that he understood everything that was before that task in that module, and also there are tasks where
they are given a little bit difficult task, where they need to find the answer by themselves"* - and *"3D deck view, 3D
models, equipment in 3D, panorama, on-ship activities"*. The prototypes are `design/task-prototypes/index.html`;
every course gets the same functionality and types, not copies of them.

**Every self-check is two parts, in this order** (content_script.py suggests it, never blocks - `t_no_challenge`,
`t_ab_order`, `t_not_spaced`):

- **Part A · check what you learned** - quick, Bloom 1-2, 2-4 minutes; covers the block just taught **and brings back at
  least one Sub-ILO from an earlier block of the module** (spaced retrieval). Best types: *true or false*, a choice with
  *how sure are you*, *build the plan* as a cause-and-effect chain.
- **Part B · find it yourself** - one harder task, Bloom 3-5, 4-8 minutes, solved with what is on the screen, not
  recalled: *work it out*, *predict*, *explore*, *investigate*, *check a colleague*, and on board in 3D: *line it up*,
  *inspection round*, *take it apart*, *test before entry*. Difficult because it is real, never difficult for its own
  sake (owner: "interestingly difficult").

The mix is L38: a self-check has at most 2 basic tasks (choose, match, order) and the rest rich - 3 + 2 in a set of
five (`content_script.py` `t_sc_mix`, always a must-fix). Rich is the locate, operate, investigate and build families,
a scenario or a prediction, and anything on a 3D model or an animation. With no equipment to show, pick from: spot the
error in a real document, check a colleague, find the fault, build the plan, fill the matrix, a scenario whose choice
has a consequence.

**Which task to pick - make it engaging** (the expert reviewer: "not the same drag-and-drop tasks every time"):
- vary by **family**, not by name (match, sort and order are all dragging cards): in every set no two neighbours of one
  family, no family over about 40 %, three families in a set of four or more (`t_family_run`, `t_family_share`,
  `t_few_families` - a note everywhere: the writer follows it, the build is not stopped by it);
- Part B on the module's **running case** - the group's own ship or project;
- a **consequence** for a choice (scenario, predict), a **real document or photograph** to work on;
- **one team task a module** where a Sub-ILO is Bloom 3+: a team case, plan or drill with roles (leader, recorder,
  checker) in place of one self-check's Part B (`"team"` on its task slide; `t_no_team` notes a module of 90+ minutes
  without one).

**Clear what to do** (the owner: "the trainee must easily understand what to do"): every task page says under the question
what to do (`task_pages.py` `what_to_do`) - a multi-select how many to tap, a calculation its unit and rounding. The
script check refuses a question that asks two things and a calculation without its unit or rounding, and notes a "not"
or "except" that is not written in capitals.

**The debrief rule (every task page).** A wrong answer says **Not right.**, the question's `brief` reason (one short
line that never names the right answer - content_script.py refuses one that does) and *we will check this one together
in the debrief*. The right answer is never shown on the tablet - not on the question, not on the result screen; the
classroom's debrief shows it, whole, when the instructor reveals it, so the class works it out together. A right answer
still shows its why. The page carries `data-reveal="debrief"`; `"feedback": "now"` at the top of a build sheet keeps the
older reveal for a course whose owner wants it. The classroom receives every item whole - question, answer,
right answer, why, the brief reason (`n`) and how sure (`sure`) - never cut to 90 / 120 characters again - and, for counting across classes, the question's id (`q`), the key of each choice made (`p`) and how sure as a number (`s`). **A self-check is answered once:** every part locks at its Check, and
the result screen has no Start again - a trainee who got it wrong hears why in the debrief, not by trying again. **The wrong ideas behind the wrong choices** are tagged per module once its tasks are built (`compile/scripts/debrief_map.py draft` → fill the tag file → `check` → `review` for the operator → `approve --by`): one id per wrong belief, shared by every choice that leads to it, and `safety` on a question where believing the wrong thing can hurt someone. The debrief then groups the class by those ideas, safety first. The map lives in the module's instructor folder and never reaches a tablet.

The types (`true_false`, `calculate`, `predict`, `explore`, `investigate`, `critique`, `line_up`, `inspect_round`,
`take_apart`, `test_atmosphere`, plus `"confidence": true` on any question and the `"look": "chain"` of
`build_the_plan`) and their part (A or B) are in `media-and-tasks.json` → `mechanics`; each is graded by a key per
item, or over a tolerance, never by reading prose. Rules that hold for them: the critique sheet never says which
claims are wrong (every claim offers "keep it as written" and the same number of choices); a take-apart card names a
part and what it is made of, never what it is for; a reading taken too early in *test before entry* does not count, and
the entry decision follows as its own question; *how sure are you* counts *certain but wrong* - where the debrief starts.

The runtime is `assets/gb_interact.js` + `gb_interact.css` (shipped with gb_answer.js, loaded before it); the formats
are `course-factory/scripts/interact_formats.py`; the compiler is `compile/scripts/interact_pages.py`. What the
operator's text cannot say - a 3D scene, a pipe network, a model's expressions, a photograph - is the build sheet's
(`interact_pages.py` docstring). A 3D type is drawn by the factory's 3D kit (`course-visuals/kit3d`, the deck's own parts
and look); the starting points are `templates/interact/` - `deck_lineup`, `compressor_room` and `ball_valve` scenes with
their build-sheet entries, and `example_set.json`, a whole Part A + Part B set. A task scene is NOT labelled where a
label would give the answer away (check_kit3d.py's "a part nobody names" is expected there).

Fingers first, as everywhere (§0): every drag has a tap, every pinch has + and -, a 3D tap forgives a near miss, 56 px
targets, nothing hover-only. Nothing on a self-check or module check is typed: the calculator is buttons.

---

## 3 · Navigation — the rules broken most often

> **L35:** the trainee tablet has **no task list**. A task opens on every trainee tablet by itself when the
> instructor presses OPEN TASK on the instructor's panel, and only then. The trainee cannot see all tasks on one
> page or open another task, and there is **no "all tasks", "module tasks" or "back to tasks" button**. The slide on
> the classroom screen only says that a task starts now. At the end of a self-check or module check the trainee sees
> their own score (it does not count).

- **Every route out has a route back** — to the exact page it came from, never via the module list.
- **Never end a task with a row of unexplained buttons**, and never offer to jump to a different
  numbered task.
- **Returning must not re-ask for the session code or flash the start screen.** A page linking
  back into the shell carries a route hash; the shell pins the resumed state with a class.

---

## 4 · Understandable without a wall of text

The test: **someone who has never seen the task can tell what to do from the screen alone.** Text
is allowed; text as the *only* mechanism is not.

- **State visible at all times** — which part, how many left, what is right. A bar, not a paragraph.
- **One live action** — exactly one control is obviously the thing to press.
- **The answer's shape is visible before the answer** — six slots for six findings.
- **Progressive disclosure** — Part 2 is not on screen while Part 1 is unfinished.
- **Show, then ask** — the document and the question on the same screen.

---

## 5 · Typed input must have a way out

Wherever a text field is unavoidable (a simulator or field reporting task), the soft keyboard is dismissible **from the screen**, by three
routes: `enterkeyhint="done"` on every single-line input · **Enter blurs a single-line input**
(textareas exempt) · a **"Done ✓" pill**, shown only while a field has focus, at least 44 × 44,
never covering the field — the one route that must never be dropped. Engine-level, not per-page:
load `assets/kbd_escape.js` + `assets/kbd_escape.css`; the wiring is in `references/typed-input.md`.

---

## The look of a task page is not this skill's to invent

Load, in this order:

```html
<link rel="stylesheet" href="../assets/gb_tokens.css">   <!-- course-module-ui -->
<link rel="stylesheet" href="../assets/gb_page.css">     <!-- course-module-ui: the page frame -->
<link rel="stylesheet" href="../assets/gb_task.css">     <!-- here: the task controls -->
```

All three — and the task engines `kbd_escape.*` and `task_complete.*` — are already in the module's
`assets/`: `course-module-ui/scripts/design_system.py install` copies them. Do not open them to use
them; the class names are in `course-module-ui/references/vocabulary.md` §7.

`gb_task.css` owns the state bar, the question stem, the 56 px option, the why panel and the
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

**Cap the taps** at the number asked for · **tapping a mark removes it**, plus **Erase all** ·
hints subtle and brief (a short low-opacity glint), never permanent circles · **never number the
targets** in a helper list when they are asked for in that order · the recognisable photograph goes
in the **feedback**, not beside the data the trainee is meant to read.

---

## 7 · Real photographs

Prefer a real photograph; draw only what no photograph can show and **say on the page that it is a
drawing**. Licence and credit on the page · **open the file and look at it** first · a caption claims
only what the photograph evidences · **every picture opens full screen and closes again** - load `../assets/gb_zoom.js` + `gb_zoom.css` on every task page with a picture (L51; a picture the trainee answers on gets a ⤢ corner button by itself, so a tap stays the answer).

---

## 8 · Two-stage tap, and close buttons

1. **First tap opens the card and nothing else** — including a tap on the picture.
2. **Only an open card lets its picture go full screen** (the shared viewer, `gb_zoom.js`, does this by itself).
3. **Always a close button**, at least 48 × 48, on the opened card and the full-screen view.
4. **The tap hint never sits on top of content** — "tap to open" in normal flow beneath a closed
   card's picture; a badge over the picture only on an opened card.

---

## 9 · Completion is explicit, and the same everywhere

Every task ends with a state saying **the part is finished** and **what happens next**, driven by one
shared engine: load `assets/task_complete.js` + `assets/task_complete.css` and call it from the
task's own finish handler.

- **A panel, not an `alert()`**, and dismissible — the reasons behind it are the point.
- **Quiet.** A self-check and a recorded check differ by one line of ordinary type. The panel never
  says "PASSED".
- **Never animate it into visibility.** Its resting CSS state must already be visible — a 10px
  transform is safe; a fade is not.

### 9a · The classroom rulebook

The classroom's rules for a task page — answers never readable in the page (`data-key`, `gbKey`), the timer
(`gb-timer`, `timeout: true`), one opening and one result, the result screen as the last screen with nothing to
press, a task never leaving its own page, and team tasks — are in `course-factory/knowledge/classroom-system.json`
→ `task_page` and `team_task`; `check_script_match.py` and `check_course_package.py` check them. L42 applies in full
to a team role: its part is as plain and as big as everything else.

---

## 10 · Never ask a trainee to record a number the screen does not show

**Every number any record asks for must be visible on the trainee's screen at the moment it is asked
for** — rendered, not derivable. Check both directions, against the record sheet: each number the
record names → the element that paints it; each total the task computes → where it is written to
the page. `scripts/check_task_pages.py` flags candidates; the record sheet is the authority.

---

## 11 · Measurable floor — verify, do not assume

At the target viewport (**1280 × 800 landscape** for the classroom; 800 × 1280 portrait for the old app's
reference build), on every task screen:

| | Requirement |
|---|---|
| Type-size and target floors (listed only here) | slide body text **22 px** (`floor.json` `body_text`, at 1024 × 768 and 1280 × 800) · question **18 px** · answer **16 px** · any text a trainee reads **12.5 px** · tap target **44 × 44 CSS px**, no exceptions · answer control **56 × 56 px** (L42) |
| Contrast | **≥ 4.5 : 1** (3 : 1 for large text) against the *resolved* background |
| Horizontal scroll | **none** — wide tables and drawings scroll inside their own container |
| Overlap | **none** — no text over text, nothing escaping its container |
| Console | **no errors**; every widget initialises |
| Network | **no requests** beyond an already-accepted font link |
| Keyboard | if there is a text field, all three routes out of §5 present |

**The browser measurement is the authority. Every static check is a pre-filter.** A clean report
from an unverified probe is worse than no report — read **`references/verify.md`** before reporting
any measurement.

**11.1 · `clamp(MIN, COEFFICIENT, CEILING)` resolves to exactly one of the three.** Compute all three
at the target viewport, take whichever binds, and judge only that. `scripts/check_task_pages.py
--only floor` does this and names the binding dial; `--viewport WxH` defaults to `1280x800`.

---

## 12 · After any scripted or templated edit, load the page and read the console

An inline script is all-or-nothing: one bad token disables every control on the page with no visual
symptom. **Any edit made by a script, a template, a regex or a bulk find-and-replace is not finished
until the page has been loaded and the console read.** `scripts/check_task_pages.py` runs
`node --check` on the inline scripts; where `node` is absent it says so and exits non-zero for that
check, and the browser console becomes the only syntax check.

---

## 13 · Dead markup, and specs that outrun the code

Sweep with `scripts/check_task_pages.py`: an **id or `data-` hook** nothing reads is deleted; a
**class styled but present in no markup in scope** is deleted from those stylesheets; and
`--only states` — **a class the engine adds at run time that no stylesheet styles**. The answer states
are `sel`, `right`/`ok`, `wrong`/`no`, `dim`, `why.good`/`why.bad` and `.sub`; `assets/gb_task.css`
carries them all. Read the engine before styling a name — `.sub` is a full-width 56px button, and
`.part2` is `display:none` until the engine reveals it.

> **A rule stated in a skill or a spec that the reference implementation does not actually follow is
> wrong in the skill, not missing from the code.** Find out which one shipped and worked before
> changing either.

---

## 14 · Shared engines drift, and generated builds overwrite

Engines are usually per-module copies: **a fix to one is a fix to none** — apply it to every module
in scope, or record the drift as a `PROVISIONAL` with the reason. A generated single-file build
overwrites hand edits: edit the authored sources and re-run the build.

**Never change course content while doing UX work** — wording of questions, answers, explanations,
values, units, terminology or source citations. If a UX fix seems to need a content change, stop and
report it as a `[VERIFY: …]` line rather than making it.

---

## Honesty markers, and the notes file

The marker set and its rules are in `novikontas-course-start`. Land every marker in the notes file so nothing is
used and never reported; never invent a photograph's licence or credit, a regulatory reference, or an answer key.
Markers live in `data-` attributes, `data-cue` or the notes file - never in visible text on a trainee page
(`course-factory/knowledge/slide-text-rules.json` → honesty_markers). Write **`templates/task-notes.md`** during the
run, not afterwards.

---

## 15 · Every number a screen states must match the page

Any number a deck, plan, score sheet or reference states about a task — question count, pass mark,
attempts, minutes — is **derived from the task page or not stated at all**. In prose, state the
count read from the page (*"10 questions"*) - a self-check or module check shows a score and no pass mark; grep the number across
**every** tree before believing it is only in one place; and check the attempt policy against the
page's own buttons, not its prose.

## 16 · Nothing is useless until you grep for what depends on it (L7)

Grep the id, class, label and filename across **both tablet trees, the course tree and every generated script**, read
the consuming code's **null branch**, and say what you checked.
