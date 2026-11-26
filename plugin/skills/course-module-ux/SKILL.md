---
name: course-module-ux
description: Use whenever building, converting or signing off the delivered HTML of an instructor-led training module that runs as ONE page — open the HTML, press Start, press Next to the end, never navigating away mid-session. Owns the one-page architecture, what a projected screen may show a trainee versus what belongs on the instructor's own device, the instructor run script generated from the deck's own markup, and the measurement discipline that keeps a contrast, geometry or type-size report from being falsely clean. Trigger on "module page", "START HERE", "step runner", "press Next", "one page per module", "a block has no screen", "contrast audit", "slide overflow", "run script". Course-agnostic. Not trainee task screens (course-task-ux), not the deck engine (novikontas-presentations), and never what a module teaches.
---

# Course module UX — one page, press Next to the end

> **Every reply to the operator** (L25): three parts as short points - **Done · Check now · Next** -
> in everyday words, for someone who knows nothing about IT. The full rule: `course-factory/SKILL.md`.

**The acceptance test.** A person who has never seen the material opens the module's one HTML
file, presses **Start**, and presses **Next** until the session is over — and a real class gets
taught. Nothing is navigated to. Nothing is hunted for.

Owner, verbatim: *"it should be like open html, and dont navigate to other page, just start
module, next next next next next and thats how until end."*

Three consequences, and they are the whole architecture:

1. **Zero `<a href>` inside any slide.** A link inside a delivery screen is the old model
   leaking back in. Landing-screen and footer links are fine — they are not inside a slide.
2. **Everything the session needs becomes a screen.** An activity launch, the run of a
   practical, what is marked, the debrief, the module check. If a block of the timetable has no
   screen, that block does not happen: one module was silently skipping 90 of its 220 minutes
   because two blocks had no screen at all.
3. **The landing page opens the presentation straight away** (L43). The step runner ("open the
   presentation and finish it", with the real minute total, then the closing record step) exists
   only in `START_HERE_EXTENDED.html` and in modules built before L43.

This is a **delivery-UX skill**. It never decides what a module teaches.

---

Design is the person's (L26): tell them the risk first, then record their choice with `design_choices.py add` (course-factory); it is never changed back.

## Where a module lives, and how it starts (L43)

*(L45: the folder is `course\modules\module01\` and the deck `presentation\index.html` - every screen a `.slide`
with `data-title`, the instructor notes in `data-cue`, a task slide with `data-activity` + `data-task-href`;
`course-factory/knowledge/classroom-system.json` is the authority.)* Every module is built into its own folder, with everything it needs inside it
(`presentation\`, `tasks\`, `instructor\`, `assets\` - styles and scripts copied in). **`START_HERE.html` opens the
presentation straight away**; **`START_HERE_EXTENDED.html`** is the fast-access page - a button for the presentation,
every task, the module plan, the instructor notes. `course-factory/scripts/check_module_folder.py` proves it.

## Pick the mode, then read one lane

Read only the lane the task needs: `build/GUIDE.md` (a module page from scratch, or more screens) ·
`convert/GUIDE.md` (off the old multi-page model; `measure/GUIDE.md` at its step 9) · `runscript/GUIDE.md`
(the instructor's running order from the deck) · `measure/GUIDE.md` (measuring, auditing, sign-off).

Not here, point at them: the look → `course-module-ui` · trainee task screens → `course-task-ux` · deck engine, House
Rules, copy budgets → `novikontas-presentations` · start page / delivery package → `novikontas-course-start-page` ·
exercises, ILOs, pedagogy → the `novikontas-*` family.

---

## The seven laws that hold in every mode

These are short on purpose. The lane guides carry the mechanics.

**1 · The audience rule — per item, never per screen.** Owner, verbatim: *"if there is info
that is necessary for trainee leave there, if its strictly for instcutor, put in instcutors
tablet."* The criteria a trainee is judged on **stay on the projected screen**; the craft of
marking them **moves**. Apply it item by item — a screen is almost never wholly one or the
other.

The test that catches the failure: **a second-person "you" on a projected screen that actually
means the instructor is a defect.** *"the technique you demonstrated"* reads to a trainee as if
they demonstrated it.

**2 · `data-cue` is the instructor-only channel.** An attribute on the slide, never rendered,
revealed on the instructor's own key. Anything borderline goes there rather than into the
visible body. It is why the audience rule costs nothing — the material is not lost, it is
routed.

**3 · Compact.** The instructor's own surfaces (a runner step, a pre-flight item, a page opened
mid-session) have a word budget and it is small; slide words follow `course-factory/knowledge/theory-rules.json`
(slide), where going over a budget is a note. Long prose is the defect this system exists to remove, and it
returns on every module unless actively cut. But **visible must be sufficient, not merely short** — a 60-word screen that
cannot be acted on without opening a `<details>` is worse than the 300-word screen it replaced,
because it now hides the thing you need *and* looks finished. A set point, a limit or a
maritime term in a visible line is the content, not clutter. Compact never overrides an operator
who asks for more explanation (L26): the extra explanation goes onto **more screens**, not denser ones.

**4 · Navigate on the screen; explain in the notes.** The projected screen says what to open, what the
trainees do, and when it is finished. *Finished when* is the highest-value line there is: without it nobody
knows when to press Next, and that is the whole mechanism. The full explanation goes to the instructor's channel
(`data-cue`, L29) as **Say / Ask / Show**, 20-150 words (`course-factory/knowledge/theory-rules.json`).

**5 · Paperless.** The lesson itself needs no printer on its delivery path: every screen, task and run step works
from the tablets and the projector. Purge the wording as well as the behaviour — "print one per group",
`☐ yes ☐ no` glyphs, blank ruled rows, "photograph the filled screen". Print stylesheets may exist; **no lesson step
may depend on them.** Paper items (laminated cards, handouts, additional-materials) are extras the factory also
writes; the lesson runs without them. A factual reference to a source document that is itself printed stays.

**6 · The deck runs on the instructor tablet (1280 × 800) and the classroom screen; tasks run on the
trainee tablet** (L35). The tablet (1280 × 800 landscape) is judged first, 1024 × 768 is stated, and the
projector (1920 × 1080) is checked once at the end — `measure/knowledge/floor.json` → viewports. A finger first: no hover-only affordance, ES5 in shared engines, a
sticky action bar with `env(safe-area-inset-bottom)`, and `:has()` mirrored with a class
because old Android WebViews lack it. The type-size and touch-target floors are listed once, in `course-task-ux` §11.

**7 · "Why is this here?" means explain it — it does not mean delete it.** A reader who cannot see the point of
something has reported on the presentation, not proved the thing useless. Find its job first; if it has one, keep
it, say its job in plain words and move it to where that job happens (a safety document becomes a ticked pre-flight
line; an audit code a collapsed disclosure plus a footer mapping; a number with no delivery use goes to the footer).
When the operator **tells** you to remove something, remove it (L26) — grep first for what depends on it (L7).

**Do not restyle.** When a module feels wrong the cause is almost always information
architecture or word count, not colour. Diff the design tokens before touching them.

When the look genuinely *is* the question — a new deck's palette, a screen that does not
match Module 1, "which radius" — that is `course-module-ui`'s. This skill owns the **floor**
(`measure/knowledge/floor.json`: contrast, fill, overflow, sizes); a floor is a minimum, not an identity. Load
`course-module-ui` before writing the first stylesheet of a new module (build step 8, required).

---

## The gate — the screen inventory, approved before anything is built

Building or converting a module page is the expensive step: every screen carries markup, graphics and
measurement. Changing a row in a table is free; rebuilding fourteen screens is not.

So before writing any HTML, work out **one table**. When the module is compiled from an approved content
script, the table is printed for the record and the build goes on - no stop. Wait for approval only for a
hand-built module with no approved script:

| # | Screen | Kind | Block / minutes | Activity code | What is on it | Cue moved off it |
|---|---|---|---|---|---|---|

Every row of the timetable must appear. A block with no row is the 90-missing-minutes defect,
and the table is the only place it is cheap to notice.

This table is **derived from the module's approved content script** (`course-factory`
`script/GUIDE.md`, L29) — one row per script screen, in its order — and is not a second approval of
the words. Build every screen with `data-script="<id>"` and the approved text in
`data-script-field` elements; `check_script_match.py` proves the deck says exactly that. A block of
the timetable the script has no screen for is still the defect above: send it back to the script.

---

## Honesty markers

The marker set and its rules are in `novikontas-course-start`. Never fill a gap plausibly; never invent regulatory
content, a quoted criterion, a set point, or a QR code. Markers live in `data-` attributes, `data-cue` or the
delivery notes - never in visible text on a trainee or projected page
(`course-factory/knowledge/slide-text-rules.json` → honesty_markers). **Every marker you write into an artefact must
also land in the delivery notes:** copy `templates/DELIVERY_NOTES.md` next to the module and fill it during the run,
not afterwards.

---

## The engine and the shell

Do not write a deck engine. `assets/gb_deck.js` is it: `GBDeck.init({text, hooks})` owns
start/exit, next/prev, progress, counter, block tag, overview, instructor cue, fullscreen,
keyboard (with a keyCode fallback), guarded swipe, idle chrome and per-screen enter/leave/step hooks.
It pairs with `course-module-ui/templates/gb_shell.css` and `gb_shell.html`. All three reach the
module through `course-module-ui/scripts/design_system.py install` — copied, never retyped, and the
engine is not read to use it: its API is the line above.

If a deck has more than one slide and no `#btnNext`/`#btnPrev`, the engine paints a red banner
across the page saying so. That is deliberate: the pilot shipped a module a finger could not
advance, and a silent failure is how it got that far.

**A figure that builds in steps is walked by the deck's own Next.** Its slide's hook carries
`step(dir)` (true while it has a step that way, false when the deck should move on), so Next,
Back, the arrow keys and a swipe show every step before the slide changes. Never a per-module
copy of this: M01 and M02 each carried one and M03 was built without it, so its figures were
skipped in front of a class. A line a step lights must stay readable in its lit state — white
text on a light wash is the trap. `audit_drive.js` walks and measures every step, and fails a
slide the deck's Next leaves with steps still to show.

## Verify before reporting done

Run the checks; do not assert them. The probes, their exit codes and the measurement traps that make a clean report
untrustworthy are in `measure/GUIDE.md` — read it **when you reach sign-off**, not before. Passing one layer says
nothing about the others: STATIC (`measure/scripts/check_static.py`, `check_navigation.py`) · RUNTIME
(`audit_drive.js` with `audit_deck.js` and `audit_collide.js` loaded first, `audit_drawing.js`,
`course-visuals/scripts/verify_figures.js`) · COMPOSITION (`audit_compose.js`) · HUMAN (`walk_review.py`,
`course-visuals/review/GUIDE.md`). Report what failed as plainly as what passed; if something cannot be verified in
the session, say so and name what would.

Serve over http — `measure/scripts/serve_fresh.py <course>`, a fresh port after every edit — then
in the page:

```js
await AuditDrive.run()          // every slide, driven by the deck's own Next button
await AuditCompose.run()        // every slide, is it composed or does it just fit
GBVerifyFigures.run({})         // every figure mount, measured
```

### Composed, or merely fitting?

`audit_deck.js` reports a `fill` percentage computed from container boxes. **A large empty
container scores a high fill while the only thing a learner can read sits in its corner.** That
number is not evidence of composition and must never be reported as if it were.

`audit_compose.js` measures **meaningful content** — headings, copy, list items, table cells, svg,
img, canvas, controls — and ignores the div, panel or card holding them. Furniture inherits its
right to the space from what it contains. It reports:

| | |
|---|---|
| `ink` | union area of meaningful content, as a share of the stage |
| `centroid` | where the weight actually sits, x and y, 0..1 |
| dead half | a half holding under 8 % of the ink — the corner-cluster detector |
| `focal` / `focalW` | the largest single element, by area and by width |
| verdict | COMPOSED · REVIEW · WEAK |

Vertical drift is checked as well as x, and a figure is undersized only when it is small in its own dominant axis
too (area alone is a landscape assumption).

A WEAK verdict is a defect. A REVIEW is a call for a human to look, not an automatic failure —
`data-compose="sparse"`, or a named composition on the body, declares intent and the ink floor
is not applied.

Run it at **1280 × 800** (the viewport that judges; `measure/knowledge/floor.json` → viewports). The defaults already match the canonical shell
(`.slide`, `active`, `#startBtn`, `#btnNext`), so a deck built on it needs no CONFIG edit.

Static checks cannot see contrast as painted, a control under the chrome, or a dismissed screen still swallowing
taps. **A number in a report is a finding:** `linksInsideSlides: 17` was printed and read past.
