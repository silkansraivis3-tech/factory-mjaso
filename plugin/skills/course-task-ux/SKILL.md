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

**v2 (2026-09-03) · Maintained by Raivis · part of the `course-factory` plugin, shared with colleagues through the marketplace**

Ruled by a course owner across 2026-09-01/03 while reviewing a tablet build of 32 task
screens across eight modules. The owner quotes that are the evidence — why each rule exists and
why it is not negotiable on style grounds — are in `references/rulings-in-full.md`. They are
quoted from a previous course; **none of them are about your course's content.** "Not negotiable"
means the factory never relaxes them on its own; it never means refusing an operator's request (L26).
If a request collides with one, say which in a sentence, offer the closest option that works, do it.

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
| a rule is in question, or before relaxing or changing one | `references/rulings-in-full.md` — the owner's rulings and the failures behind them, same section numbers |
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

> **The owner's rulings behind every section below — the quotes, the failures and the numbers —
> are in `references/rulings-in-full.md`, word for word, under the same section numbers.** Read a
> section in full before arguing with it, relaxing it or changing it.

## 1 · What a task screen must NOT have

- **No header block** — no course name, module number, task code, "in-class activity" label,
  time estimate, ILO or Sub-ILO code, or scored-item count. The trainee arrives from a card that
  already showed the title. The task begins with the task; keep only the injected back-link.
- **No handout advertising.** A single contextual deep link inside a task is acceptable where it
  genuinely helps mid-task; a "the handout is yours" card is not.
- **No printed-worksheet thinking** — no "read this page, then go to another page, then type your
  answer in", and no group-work tasks unless the delivery has a system for grouping trainees.
- **No fake or duplicated furniture** — no mock-up of the app's own UI, no "SCREEN 1 OF 4" counters.

---

## 2 · How a trainee answers

**Self-checks and module checks: choosing, not writing.** Allowed: **tap to choose** · **tap to
locate** (§6) · **order / sequence** · **match** · **choose-and-justify** (pick the action, then the
reason from a set — both must be right).

**Free typing is allowed in exactly one place:** a simulator or field reporting task. If it is
allowed, §5 becomes mandatory.

**One Submit per part.** Correct items lock and grey out with an explanation of *why*; wrong items
get a hint and another attempt. The reasoning lives in the task, which is why the deck needs no
answers slide.

---

## 3 · Navigation — the rules broken most often

- **Every route out has a route back** — to the exact page it came from, never via the module list.
- **Never end a task with a row of unexplained buttons**, and never offer to jump to a different
  numbered task.
- **The task list is numbered by position** — 1, 2, 3, 4 — not by category letter or course code.
  Reference-material cards keep their own glyph.
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

Wherever §2 permits a text field, the soft keyboard is dismissible **from the screen**, by three
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

**Cap the taps** at the number asked for · **tapping a mark removes it**, plus **Erase all** ·
hints subtle and brief (a short low-opacity glint), never permanent circles · **never number the
targets** in a helper list when they are asked for in that order · the recognisable photograph goes
in the **feedback**, not beside the data the trainee is meant to read.

---

## 7 · Real photographs

Prefer a real photograph; draw only what no photograph can show and **say on the page that it is a
drawing**. Licence and credit on the page · **open the file and look at it** first · a caption claims
only what the photograph evidences · photographs a trainee identifies from are tappable to full size.

---

## 8 · Two-stage tap, and close buttons

1. **First tap opens the card and nothing else** — including a tap on the picture.
2. **Only an open card lets its picture go full screen.**
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

---

## 10 · Never ask a trainee to record a number the screen does not show

**Every number any record asks for must be visible on the trainee's screen at the moment it is asked
for** — rendered, not derivable. Check both directions, against the record sheet: each number the
record names → the element that paints it; each total the task computes → where it is written to
the page. `scripts/check_task_pages.py` flags candidates; the record sheet is the authority.

---

## 11 · Measurable floor — verify, do not assume

At the target viewport (**800 × 1280 portrait** for the reference build), on every task screen:

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

**The browser measurement is the authority. Every static check is a pre-filter.** A clean report
from an unverified probe is worse than no report — read **`references/verify.md`** before reporting
any measurement.

**11.1 · `clamp(MIN, COEFFICIENT, CEILING)` resolves to exactly one of the three.** Compute all three
at the target viewport, take whichever binds, and judge only that. `scripts/check_task_pages.py
--only floor` does this and names the binding dial; `--viewport WxH` defaults to `800x1280`.

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

## 15 · Every number a screen states must match the page

Any number a deck, plan, score sheet or reference states about a task — question count, pass mark,
attempts, minutes — is **derived from the task page or not stated at all**. In prose, state the
proportion with the count after it (*"75 % of the check, currently 8 of 10"*); grep the number across
**every** tree before believing it is only in one place; and check the attempt policy against the
page's own buttons, not its prose.

## 16 · Nothing is useless until you grep for what depends on it

Before listing anything as useless: grep the id, class, label and filename across **both tablet
trees, the course tree and every generated script** · read the consuming code's **null branch** · ask
whether a **planned** system needs the data · then report, and say what you checked.
