---
name: course-module-ux
description: Use whenever building, converting or signing off the delivered HTML of an instructor-led training module that runs as ONE page — open the HTML, press Start, press Next to the end, never navigating away mid-session. Owns the one-page architecture, what a projected screen may show a trainee versus what belongs on the instructor's own device, the instructor run script generated from the deck's own markup, and the measurement discipline that keeps a contrast, geometry or type-size report from being falsely clean. Trigger on "module page", "START HERE", "step runner", "press Next", "one page per module", "a block has no screen", "contrast audit", "slide overflow", "run script". Course-agnostic. Not trainee task screens (course-task-ux), not the deck engine (novikontas-presentations), and never what a module teaches.
---

# Course module UX — one page, press Next to the end

**v1 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

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
3. **The step runner survives but collapses to about two steps** — "open the presentation and
   finish it", with the real minute total, then the closing record step. It announces the day;
   it is not the thing you click through.

This is a **delivery-UX skill**. It never decides what a module teaches.

---

## Pick the mode, then read one lane

Read this router fully. Then read **only** the lane the task needs. The lanes never run
together, and loading two means the mode was not decided.

| Mode — what the task actually is | Read |
|---|---|
| Building a module page from scratch, or adding screens to one | `build/GUIDE.md` |
| Bringing a module off the old chained / multi-page model | `convert/GUIDE.md` |
| Generating or regenerating the instructor's running order from the deck | `runscript/GUIDE.md` |
| Measuring, auditing, or signing anything off | `measure/GUIDE.md` |

Converting also finishes with a measurement pass — read `convert/GUIDE.md` first and
`measure/GUIDE.md` at step 9, not both up front.

### Deliberately outside this bundle — point at these, never copy them

| Concern | Skill that owns it |
|---|---|
| The **look** — palette, typography, light and dark/photo modes, the header band, cards, pills, the takeaway, semantic status colour, every token | **`course-module-ui`** |
| Trainee task screens: what a task may contain, how a trainee answers, two-stage tap on card grids, photographs, the task floor | `course-task-ux` |
| The deck template engine, House Rules, slide roles, copy budgets, `build.py` | `novikontas-presentations` |
| The offline start page / delivery package / "which file do I open first" | `novikontas-course-start-page` |
| Exercise design, course intake, ILOs, pedagogy, assessment design | the `novikontas-*` course-design family |

If a task is really one of those, stop and load that skill instead. A copy of org knowledge
goes stale the moment the original is revised, and nobody finds out until it is wrong in front
of a trainee.

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

**3 · Compact or it does not ship.** Every surface has a word budget and it is small. Long
prose is the defect this system exists to remove, and it returns on every module unless
actively cut. But **visible must be sufficient, not merely short** — a 60-word screen that
cannot be acted on without opening a `<details>` is worse than the 300-word screen it replaced,
because it now hides the thing you need *and* looks finished. A set point, a limit or a
maritime term in a visible line is the content, not clutter.

**4 · Navigate; do not narrate.** Say what to open, what the trainees do, and when it is
finished. Do not write out what the instructor should say — they know their subject and their
room, speech scripts double the length of everything and get skipped in delivery.
*Finished when* is the highest-value line there is: without it nobody knows when to press Next,
and that is the whole mechanism.

**5 · Paperless.** Nothing in the delivery path may require a printer. Purge the wording as
well as the behaviour — "print one per group", `☐ yes ☐ no` glyphs, blank ruled rows,
"photograph the filled screen". Print stylesheets may exist; **no workflow may depend on
them.** A factual reference to a source document that is itself printed stays: that describes
the source, not the workflow.

**6 · The tablet is the primary device, the projector is the second.** A finger on an
800×1280 portrait screen first, then check it survives landscape and a projector — never the
other way round. Touch targets **≥ 44 px**, no hover-only affordance, ES5 in shared engines, a
sticky action bar with `env(safe-area-inset-bottom)`, and `:has()` mirrored with a class
because old Android WebViews lack it.

**7 · "Why is this here?" means explain it — it does not mean delete it.** When a reader
cannot see the point of something, that is a report about the presentation, not proof the thing
is useless. Find its job first. If it has one, keep it, say its job in plain words, and move it
to where that job happens. **Cutting usable material to satisfy a complaint is a worse defect
than the clutter was**, because the clutter was visible and the loss is not. The three moves:
a safety-critical document becomes a ticked line in the work's own pre-flight; an audit code
becomes a collapsed labelled disclosure plus a footer mapping; a number with no delivery use
goes to the footer.

**Do not restyle.** When a module feels wrong the cause is almost always information
architecture or word count, not colour. Diff the design tokens before touching them.

And when the look genuinely *is* the question — a new deck's palette, a screen that does not
match Module 1, "which radius", "why do these two modules look different" — that is
`course-module-ui`'s, not this skill's. This skill owns the **floor**: contrast ≥ 4.5, text
≥ 12.5 px, targets ≥ 44 px, fill, overflow. A floor is a minimum, not an identity — two people
can pass every check in `measure/knowledge/floor.json` and ship modules that look unrelated.
Load `course-module-ui` before writing the first stylesheet of a new module; it is step 8 of
`course-factory`'s build order and it is required, not optional.

---

## The gate — the screen inventory, approved before anything is built

Building or converting a module page is the expensive step: one module went from 6 screens to
18, and every screen carries markup, graphics and measurement. Changing a row in a table is
free; rebuilding fourteen screens is not.

So before writing any HTML, present **one table** and wait for approval:

| # | Screen | Kind | Block / minutes | Activity code | What is on it | Cue moved off it |
|---|---|---|---|---|---|---|

Every row of the timetable must appear. A block with no row is the 90-missing-minutes defect,
and the table is the only place it is cheap to notice.

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

**Every marker you write into an artefact must also land in the delivery notes.** Copy
`templates/DELIVERY_NOTES.md` next to the module and fill it during the run, not afterwards —
including its final section of feedback on this skill, which is the only channel through which
real use reaches it.

---

## The engine and the shell

Do not write a deck engine. `assets/gb_deck.js` is it: `GBDeck.init({text, hooks})` owns
start/exit, next/prev, progress, counter, block tag, overview, instructor cue, fullscreen,
keyboard (with a keyCode fallback), guarded swipe, idle chrome and per-screen enter/leave hooks.
It pairs with `course-module-ui/templates/gb_shell.css` and `gb_shell.html`.

If a deck has more than one slide and no `#btnNext`/`#btnPrev`, the engine paints a red banner
across the page saying so. That is deliberate: the pilot shipped a module a finger could not
advance, and a silent failure is how it got that far.

## Verify before reporting done

Run the checks; do not assert them. The probes, their exit codes and the measurement traps
that make a clean report untrustworthy are all in `measure/GUIDE.md` — read it **when you reach
sign-off**, not before, so a build or conversion does not carry it through the structural work.
It matters because a report of "zero contrast failures across all 16 slides" once turned
out to be 40 failures including body text at 1.08:1, and the reason was a 0.42 s CSS
transition, not the design.

Report what failed as plainly as what passed. If something cannot be verified in the session,
say so and name what would verify it.

### Static is not enough. Run the deck.

Three distinct layers, and passing one says nothing about the others:

| layer | tool | what only it can see |
|---|---|---|
| STATIC | `measure/scripts/check_static.py all <module.html>`, `measure/scripts/check_navigation.py <course>` | minutes, links inside slides, missing nav, missing back hook, declared tap sizes |
| RUNTIME | `measure/scripts/audit_drive.js` (+ `audit_deck.js`, `audit_collide.js` loaded first), `course-visuals/scripts/verify_figures.js` | contrast as painted, real laid-out size, spill, overlap, anything under the chrome, whether a figure rendered at all, whether a control can actually be tapped |
| HUMAN | `review/GUIDE.md`, the side-by-side against the reference deck | whether it teaches |

Serve over http — `measure/scripts/serve_fresh.py <course>`, a fresh port after every edit — then
in the page:

```js
await AuditDrive.run()          // every slide, driven by the deck's own Next button
GBVerifyFigures.run({})         // every figure mount, measured
```

Run it at **1280 × 800 and 800 × 1280**. The defaults already match the canonical shell
(`.slide`, `active`, `#startBtn`, `#btnNext`), so a deck built on it needs no CONFIG edit.

The first real pilot passed every static check and shipped with 75 runtime failures, including
seventeen headings at contrast 1.00, a figure whose step buttons sat below the fold behind the
chrome, and a dismissed landing screen that was still swallowing taps across the lower half of
every slide. None of that is visible in the source.

**A number in a report is a finding.** `linksInsideSlides: 17` was printed and read past.
