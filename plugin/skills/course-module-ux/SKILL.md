---
name: course-module-ux
description: Use whenever building, converting or signing off the delivered HTML of an instructor-led training module that runs as ONE page — open the HTML, press Start, press Next to the end, never navigating away mid-session. Owns the one-page architecture, what a projected screen may show a trainee versus what belongs on the instructor's own device, the instructor run script generated from the deck's own markup, and the measurement discipline that keeps a contrast, geometry or type-size report from being falsely clean. Trigger on "module page", "START HERE", "step runner", "press Next", "one page per module", "a block has no screen", "contrast audit", "slide overflow", "run script". Course-agnostic. Not trainee task screens (course-task-ux), not the deck engine (novikontas-presentations), and never what a module teaches.
---

# Course module UX — one page, press Next to the end

> **Every reply to the operator (L25):** **Done · Check now · Next**, in everyday words — the full rule is in `course-factory/SKILL.md`.

**The acceptance test.** A person who has never seen the material opens the module's one HTML file, presses **Start**,
and presses **Next** until the session is over — and a real class gets taught. Nothing is navigated to. Nothing is
hunted for.

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

## The person decides the design — L26

Every rule here about how a course **looks or behaves** governs the factory's own choices. When the person asks for
something else: nothing conflicts → do it; it goes against a rule → name the rule and the risk in one or two plain
sentences and ask **once** - *your way* / *the factory's way*; on *your way*, do it fully, record it
(`course-factory/scripts/design_choices.py add <course> --rule <id> ...`), and **never change it back** - not in a later
build, fix or session, and not because a check flagged it. The course material (programme, Main ILOs, hours, sources,
the approved words) keeps its own rules: `course-factory` SKILL.md, L26.

## Where a module lives, and how it starts (L43)

The folder is `course\modules\module01\` and the deck `presentation\index.html` - every screen a `.slide` with
`data-title`, the instructor notes in `data-cue`, a task slide with `data-activity` + `data-task-href`
(L45; `course-factory/knowledge/classroom-system.json` is the authority). Every module is built into its own folder,
with everything it needs inside it (`presentation\`, `tasks\`, `instructor\`, `assets\` - styles and scripts copied
in). **`START_HERE.html` opens the presentation straight away**; **`START_HERE_EXTENDED.html`** is the fast-access page
- a button for the presentation, every task, the module plan, the instructor notes.
`course-factory/scripts/check_module_folder.py` proves it.

## Pick the mode, then read one lane

Read this router fully. Then read **only** the lane the task needs; the lanes never run together, and loading two means the mode was not decided.

| Mode — what the task actually is | Read |
|---|---|
| Building a module page from scratch, or adding screens to one | `build/GUIDE.md` |
| Bringing a module off the old chained / multi-page model | `convert/GUIDE.md` |
| Generating or regenerating the instructor's running order from the deck | `runscript/GUIDE.md` |
| Measuring, auditing, or signing anything off | `measure/GUIDE.md` |

Converting also finishes with a measurement pass — read `convert/GUIDE.md` first and `measure/GUIDE.md` at step 9, not
both up front.

### Deliberately outside this bundle — point at these, never copy them

| Concern | Skill that owns it |
|---|---|
| The **look** — palette, typography, light and dark/photo modes, the header band, cards, pills, the takeaway, semantic status colour, every token | **`course-module-ui`** |
| Trainee task screens: what a task may contain, how a trainee answers, two-stage tap on card grids, photographs, the task floor | `course-task-ux` |
| The deck template engine, House Rules, slide roles, copy budgets, `build.py` | `novikontas-presentations` |
| The offline start page / delivery package / "which file do I open first" | `novikontas-course-start-page` |
| Exercise design, course intake, ILOs, pedagogy, assessment design | the `novikontas-*` course-design family |

If a task is really one of those, stop and load that skill instead (a copy goes stale silently once the original is revised).

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
mid-session) have a word budget and it is small; a compiled slide holds what its template holds
(`course-module-ui/knowledge/layout-templates.json` `budgets` - over it the script splits the slide or picks another
type, a must-fix) and follows the word guideline in `course-factory/knowledge/theory-rules.json` (slide). Long prose is the defect this system exists to remove, and it
returns on every module unless actively cut. But **visible must be sufficient, not merely short** — a 60-word screen that
cannot be acted on without opening a `<details>` is worse than the 300-word screen it replaced,
because it now hides the thing you need *and* looks finished. A set point, a limit or a
maritime term in a visible line is the content, not clutter. Compact never overrides an operator
who asks for more explanation (L26): the extra explanation goes onto **more screens**, not denser ones.

**4 · Navigate; do not narrate.** Say what to open, what the trainees do, and when it is
finished. Do not write out what the instructor should say — they know their subject and their
room, speech scripts double the length of everything and get skipped in delivery.
*Finished when* is the highest-value line there is: without it nobody knows when to press Next,
and that is the whole mechanism. The instructor notes in an approved content script (L29) are key
points and cues on the instructor's channel — this law is about not writing speeches, never about
leaving out what the operator asked the instructor to be told.

**5 · Paperless.** Nothing in the delivery path may require a printer. Purge the wording as
well as the behaviour — "print one per group", `☐ yes ☐ no` glyphs, blank ruled rows,
"photograph the filled screen". Print stylesheets may exist; **no workflow may depend on
them.** A factual reference to a source document that is itself printed stays: that describes
the source, not the workflow.

**6 · The deck runs on the instructor tablet (1280 × 800) and the classroom screen; tasks run on the
trainee tablet** (L35). The tablet (1280 × 800 landscape) is judged first, 1024 × 768 is stated, and the
projector (1920 × 1080) is checked once at the end — `measure/knowledge/floor.json` → viewports. A finger first: touch targets **≥ 56 px**, no hover-only affordance, ES5 in shared engines, a
sticky action bar with `env(safe-area-inset-bottom)`, and `:has()` mirrored with a class
because old Android WebViews lack it.

**7 · "Why is this here?" means explain it — it does not mean delete it.** When a reader
cannot see the point of something, that is a report about the presentation, not proof the thing
is useless. Find its job first. If it has one, keep it, say its job in plain words, and move it
to where that job happens. **Cutting usable material to satisfy a complaint is a worse defect
than the clutter was**, because the clutter was visible and the loss is not. The three moves:
a safety-critical document becomes a ticked line in the work's own pre-flight; an audit code
becomes a collapsed labelled disclosure plus a footer mapping; a number with no delivery use
goes to the footer. This law is for a *question or a complaint*. When the operator **tells** you to
remove something, remove it (L26) — grep first for what depends on it (L7) and say in one line what
else that touched.

**Do not restyle.** When a module feels wrong the cause is almost always information
architecture or word count, not colour. Diff the design tokens before touching them.

And when the look genuinely *is* the question — a new deck's palette, a screen that does not
match Module 1, "which radius", "why do these two modules look different" — that is
`course-module-ui`'s, not this skill's. This skill owns the **floor**: contrast ≥ 4.5, text
≥ 12.5 px, targets ≥ 56 px, fill, overflow. A floor is a minimum, not an identity — two people
can pass every check in `measure/knowledge/floor.json` and ship modules that look unrelated.
Load `course-module-ui` before writing the first stylesheet of a new module; it is step 8 of
`course-factory`'s build order and it is required, not optional.

---

## The gate — the screen inventory, approved before anything is built

Building or converting a module page is the expensive step: one module went from 6 screens to
18, and every screen carries markup, graphics and measurement. Changing a row in a table is
free; rebuilding fourteen screens is not.

So before writing any HTML, work out **one table**. When the module is compiled from an approved content
script, the table is printed for the record and the build goes on - no stop. Wait for approval only for a
hand-built module with no approved script:

| # | Screen | Kind | Block / minutes | Activity code | What is on it | Cue moved off it |
|---|---|---|---|---|---|---|

Every row of the timetable must appear: a block with no row is a block that does not happen, and the table is the only
place it is cheap to notice.

The table is **derived from the module's approved content script** (`course-factory` `script/GUIDE.md`, L29) — one row
per script screen, in its order — and is not a second approval of the words. Build every screen with
`data-script="<id>"` and the approved text in `data-script-field` elements; `check_script_match.py` proves the deck says
exactly that. A block of the timetable the script has no screen for goes back to the script.

---

## Honesty markers — the set, and where they land

Never fill a gap plausibly. Use exactly these four, spelled exactly this way:

| Marker | Means |
|---|---|
| `UNKNOWN` | Asked, the operator did not know. Record that it was asked. |
| `PLACEHOLDER` | Structure is right, real content is missing. |
| `PROVISIONAL` | Content exists but depends on something unapproved. |
| `[VERIFY: <what to check>]` | Asserted from a source that could not be confirmed. Always carries its payload. |

Never invent regulatory content, a quoted criterion, a set point, or a QR code.

Markers live in `data-` attributes, `data-cue` or the delivery notes - never in visible text on a trainee or
projected page (`course-factory/knowledge/slide-text-rules.json` → honesty_markers). **Every marker you write
into an artefact must also land in the delivery notes.** Copy
`templates/DELIVERY_NOTES.md` next to the module and fill it during the run, not afterwards —
including its final section of feedback on this skill, which is the only channel through which
real use reaches it.

---

## The engine and the shell

Do not write a deck engine. `assets/gb_deck.js` is it: `GBDeck.init({text, hooks})` owns start/exit, next/prev,
progress, counter, block tag, overview, instructor cue, fullscreen, keyboard (with a keyCode fallback), guarded swipe,
idle chrome and per-screen enter/leave/step hooks. It pairs with `course-module-ui/templates/gb_shell.css` and
`gb_shell.html`. All three reach the module through `course-module-ui/scripts/design_system.py install` — copied, never
retyped, and the engine is not read to use it: its API is the line above.

If a deck has more than one slide and no `#btnNext`/`#btnPrev`, the engine paints a red banner across the page saying
so, on purpose: a module a finger cannot advance must never fail silently.

**A figure that builds in steps is walked by the deck's own Next.** Its slide's hook carries `step(dir)` (true while it
has a step that way, false when the deck should move on), so Next, Back, the arrow keys and a swipe show every step
before the slide changes. Never a per-module copy of this (a module built without the copy skips its figures in front of
a class). A line a step lights must stay readable in its lit state — white text on a light wash is the trap.
`audit_drive.js` walks and measures every step, and fails a slide the deck's Next leaves with steps still to show.

## Verify before reporting done

Run the checks; do not assert them. The probes, their exit codes and the measurement traps that make a clean report
untrustworthy are in `measure/GUIDE.md` — read it **when you reach sign-off**, not before (a CSS transition still
running at measurement time can turn real contrast failures into a clean report).

Report what failed as plainly as what passed. If something cannot be verified in the session, say so and name what
would verify it.

### Static is not enough. Run the deck.

Passing one layer says nothing about the others:

| layer | tool | what only it can see |
|---|---|---|
| STATIC | `measure/scripts/check_static.py all <module.html>`, `measure/scripts/check_navigation.py <course>` | minutes, links inside slides, missing nav, missing back hook, declared tap sizes |
| RUNTIME | `measure/scripts/audit_drive.js` (+ `audit_deck.js`, `audit_collide.js` loaded first), `measure/scripts/audit_drawing.js` (inside a drawing: parts in their containers, nothing cut off, labels' safe zone - L54), `course-visuals/scripts/verify_figures.js` | contrast as painted, real laid-out size, spill, overlap, anything under the chrome, whether a figure rendered at all, whether a control can actually be tapped |
| COMPOSITION | `measure/scripts/audit_compose.js` | whether the screen is COMPOSED or merely fits — see below |
| HUMAN | `measure/scripts/walk_review.py` (the walk review); `course-visuals/review/GUIDE.md` for figures; the side-by-side against the reference deck | whether it teaches |

Serve over http — `measure/scripts/serve_fresh.py <course>`, a fresh port after every edit — then in the page:

```js
await AuditDrive.run()          // every slide, driven by the deck's own Next button
await AuditCompose.run()        // every slide, is it composed or does it just fit
GBVerifyFigures.run({})         // every figure mount, measured
```

### Composed, or merely fitting?

`audit_deck.js` reports a `fill` percentage computed from container boxes. **A large empty container scores a high fill
while the only thing a learner can read sits in its corner.** That number is not evidence of composition and must never
be reported as if it were.

`audit_compose.js` measures **meaningful content** — headings, copy, list items, table cells, svg, img, canvas,
controls — and ignores the div, panel or card holding them. It reports:

| | |
|---|---|
| `ink` | union area of meaningful content, as a share of the stage |
| `centroid` | where the weight actually sits, x and y, 0..1 |
| dead half | a half holding under 8 % of the ink — the corner-cluster detector |
| `focal` / `focalW` | the largest single element, by area and by width |
| verdict | COMPOSED · REVIEW · WEAK |

Two calibrations:

- **Vertical drift is the one the eye notices first** — the centroid is checked in y as well as x.
- **Area alone is a landscape assumption.** A wide drawing at the full width of an 800 × 1280 portrait screen covers
  20 % of its area and is using the screen as well as it can. A figure is undersized only when it is small in its own
  dominant axis too.

A WEAK verdict is a defect. A REVIEW is a call for a human to look, not an automatic failure —
`data-compose="sparse"`, or a named composition on the body, declares intent and the ink floor is not applied.

Run it at **1280 × 800** (the viewport that judges; `measure/knowledge/floor.json` → viewports). The defaults already match the canonical shell
(`.slide`, `active`, `#startBtn`, `#btnNext`), so a deck built on it needs no CONFIG edit.

A deck can pass every static check and still fail at runtime (headings at contrast 1.00, step buttons below the fold
behind the chrome, a dismissed landing screen still swallowing taps) — none of that is visible in the source.

**A number in a report is a finding** — read every count a probe prints, never read past it.
