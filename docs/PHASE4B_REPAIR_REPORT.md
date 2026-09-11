# Phase 4B — repairing the Factory from the ETPB3 pilot

Plugin **2.2.0**. Two jobs: fix the reusable problems the first real pilot exposed, and rebuild
ETPB3 with the corrected Factory. No new skills and no new agents were created; every change lands
in `course-factory`, `course-module-ui`, `course-module-ux`, `course-task-ux` or `course-visuals`.

The short version of what this phase is about: **the pilot passed every validator it had and was
still broken.** Everything below is either a defect that only the running page could show, or a
check added so the next one is caught mechanically.

---

## 1 · Module shell drift → `course-module-ui` owns a complete shell

**What was wrong.** ETPB3 carried `etpb3_ui.css`, whose first line read *"ETPB2 — shared visual
layer"*. A course-local copy of the product's own chrome, renamed once already, drifting.

**What changed.**

| file | owner | what it is |
|---|---|---|
| `templates/gb_shell.css` | course-module-ui | the deck: landing, stage, header band, footer strip, progress, chrome, overview, cue, **and now the content furniture** |
| `templates/gb_page.css` | course-module-ui | **new.** The document page: START_HERE, handout, practical cards, instructor plan |
| `templates/gb_shell.html` | course-module-ui | the markup skeleton |
| `assets/gb_deck.js` | course-module-ux | the engine |
| `assets/gb_task.css` | course-task-ux | task **mechanics only**, layered on `gb_page.css` |

The shell was incomplete, which is *why* every course wrote its own. When ETPB3 moved onto the
canonical shell it silently lost `.law`, `.warnbox`, `.fin`, `.src`, `.cap`, `.scroll`, `.meta`,
`.num` and its tables — those rules had only ever existed in the per-course file. So 2.2.0 adds the
content furniture GAS BASIC and the ETPB modules actually use, light and dark.

`gb_task.css` stopped restating the page frame. A task page is a document page with a task on it,
not a third dialect.

**Check added.** `audit_ui.py` now reads **pages**, not only stylesheets, and reports every class
used in the markup that no stylesheet the page loads defines. Fixtures:
`scripts/fixtures/fail_lost_link.html` (reproduces the exact defect, 5 findings) and
`pass_complete.html` (0 findings; the `<g class>` on a drawing is reported as a note, never a
defect).

---

## 2 · Task visual dialect → one token set

`task.css` declared itself *"shared look for ETPA1 trainee task screens"* and carried its own
`:root`: `--ink #10202e`, `--line #c8d6e2`, `--ok #0a7d55`.

Replacing the file was **not enough, and on its own made things worse.** The dialect lived in three
places:

1. `assets/task.css` → replaced by `gb_task.css`
2. **each task page's own `<style>`** → still saying `background:var(--okbg)`
3. **`style=""` attributes on SVG elements** → `fill:var(--ink2)`

An unresolvable custom property does not fall back to the previous value — the whole declaration is
invalid at computed-value time. With `--okbg` gone, the correct answer and the wrong answer both
rendered with a transparent ground and an inherited black border. Every static check was green. One
click in a browser showed it.

**Check added.** `audit_ui.py` reports custom properties a page references that nothing defines for
it, looking inside `<style>` blocks *and* `style=""` attributes. Fixture:
`scripts/fixtures/fail_dead_var.html`.

**Tokens.** Four canonical additions, each because three files had independently hand-rolled it:
`--good-wash-l`, `--warn-wash-l`, `--on-blue`, `--on-navy`. `kbd_escape.css` and
`task_complete.css` keep their drop-in `--task-*` names but now resolve them as
`var(--navy, #0A2463)` — following the canon when it is loaded, standalone when it is not.
`audit_ui.py` recognises that pattern and reports "follows --navy" instead of "not canonical".

---

## 3 · Touch navigation → a deterministic gate

`check_navigation.py` (course-module-ux/measure) asks one question: **can a finger drive this?**
Five checks — nav-js-orphan, no-touch-path, trap, no-back-hook, tap-size. Tested against a FAIL
fixture reproducing the pilot defect (4 failures) and a PASS fixture on the canonical shell (0).
Figure fragments are skipped and counted, because a fragment is pasted into a page and is not one.

ETPB3: **12 files, 0 failures, 0 warnings.**

---

## 4 · Figure mount contract → prove it at runtime

`course-visuals/scripts/verify_figures.js` is evaluated **in the page**. A mount must exist, have
children, contain an `svg`/`canvas`/`img`, lay out above a pixel floor, not be hidden, and throw no
console error. A figure on an inactive slide is activated for the measurement and restored.

ETPB3: **3 of 3 figures present, 0 console errors.**

---

## 5 · Visual QA must test the render

This is the finding that produced most of the others. The Factory already shipped
`audit_deck.js` / `audit_collide.js` / `audit_drive.js` — a driven sweep that presses the deck's own
Next button through every screen and measures what is painted. **It had never been run on ETPB3.**

First run, 1280 × 800: **75 failures.**

| what | how many | what it actually was |
|---|---|---|
| contrast 1.00 | 17 | an unscoped `.slide h3{color:var(--navy)}` I had added minutes earlier overrode the white a filled surface passes down by inheritance. Navy on navy on every activity screen. |
| spill | 48 | figures taller than the slide; on one screen the step buttons sat 40 px **below the fold, behind the chrome** |
| text under chrome | 4 | the star/delta toggles |
| text under 12.5 px | 6 | a course-local `.meta` override at 12 px beating the shell on source order |

And the one no report would have named on its own: **`#landing.gone` was still intercepting taps.**
`#landing` carries `transition: opacity .45s, visibility .45s`; where the compositor is stalled or
animations are throttled the transition never runs and the computed value stays at the *from* state
— invisible to the eye in every normal case, fully present to the hit test in the bad one.
`document.elementFromPoint` at the centre of all five figure controls returned the landing card.
Fixed with `pointer-events:none`, which no missed frame can leave behind. Same lesson the
`task_complete.css` header already records: **never let whether a control can be USED depend on a
frame having been painted.**

Other shell fixes this forced:

- `.slide{overflow:hidden}` — the stage never scrolls. `overflow:auto` let the slide scroll 177 px
  in portrait, carrying its own header band and title off the top.
- `.slide-body{overflow-y:auto}` — the net. The golden only did this below 820 px because its
  content was authored to fit a projector; a tablet deck with a tall figure overflows at 1280 × 800
  and the golden rule never fires.
- `.slide-body > *{flex-shrink:0}` — `min-height:0` seems the natural companion to a scrolling flex
  column and is exactly wrong: a shrunk mount keeps painting at full size, measured as a
  1153 × 125 px overlap of a figure on the card below it.
- `--fig-max` as a **variable**, not a fixed rule — `.slide-body svg` beats any `.thing-svg` on
  specificity, so a component that carries its own caption and control row could not tighten the
  cap. Now the shell sets the outer bound and the component inherits-and-narrows.
- The type scale is the golden deck's verbatim. It had been copied two steps small — `h2` at
  `3.5vmin` against the reference's `4.6vmin`, which on a 1280 × 800 tablet is 28 px where the
  product reads 37 px.

After: **PASS at 1280 × 800 and at 800 × 1280.** 0 low, 0 small, 0 spill, 0 tap, 0 collide.

Driven by hand as well as by probe: Start, Next, Back, the overview grid (36 items, jump, close),
fullscreen, exit to landing, the instructor cue, all five star/delta controls, and a task page
answered end to end with the semantic grounds verified by computed colour.

### The law I nearly broke

The sweep printed `linksInsideSlides: 17` and I read past it. `check_static.py` then failed the
deck 18 times, and the golden settled it: **GAS BASIC Module_01 has 27 slides and zero `<a href>`
inside any of them.** Its activity screens say it in words —

> **Now a task.** Open the tablets — **Module 1**, task `GAS101`. On your own.

ETPB3 shipped 17 launch buttons inside slides, and I had copied that treatment into `gb_shell.css`
while extracting the shell, so the pilot's deviation was on its way to becoming the Factory's rule.
Replaced with `.act-now`, an announcement. The route to a task lives on START_HERE and the landing,
both outside the deck. Recorded in `screen-kinds.json` on all four activity kinds.

**A count in a report is a finding.** That is the second time a pilot has read past its own
evidence; the first was a `check_visuals.py` warning triaged away as an architecture artefact, and
it was right too.

---

## 6 · Practical-first, measured as two tracks

One rule read as one number, and that is what went wrong.

**Track A — allocation.** What the approved programme says. External, auditable, **not editable.**
The build must claim those minutes against those buckets. ETPB3 built **650 theory / 630 practice
against an allocated 480 / 800** — under-delivering practice by 170 minutes — and `check_hours.py`
passed, because the total was right. *A total-only check cannot see a bucket swap.*

**Track B — modality.** Of the minutes in front of the room, how many have the trainee doing,
deciding, producing or saying something. A **design** metric. It changes nothing in Track A: a
theory-allocated minute delivered as an activity is still a theory minute.

**The 80 % target belongs to Track B.**

New: `course-factory/hours/scripts/check_balance.py`, and two attributes on every block-opening
screen — `data-track` (`theory`|`practice`) and `data-active` (integer minutes). The script rejects
the three ways people fake it: an active count above the block's own minutes; a practice block whose
room is receiving for most of it; a theory block claiming 100 % active, because somebody sets the
task.

### What ETPB3 actually did

The 170 minutes were **already bench work delivered under a theory label** in four cases, and
exposition that should have been bench work in two. They became drills **V1–V6** — a lighter,
observed, ungraded artefact distinct from the seven assessed practicals, with a new `drill` screen
kind and their own cards in `practicals.html`:

| | minutes | was | is |
|---|---|---|---|
| V1 | 25 | tap the plate on screen | read five values off three real machines |
| V2 | 25 | three cards about tool classes | ten instruments on the bench, three of them wrong |
| V3 | 20 | two cards about cable and lugs | **crimp one lug each** and compare against a good and a bad end |
| V4 | 30 | a drawing of where the test current flows | **take the reading**, record value, test voltage, temperature |
| V5 | 30 | calculate a relay setting on paper | **set it on a real relay's scale** and show it |
| V6 | 40 | "reserve" | three named routes at the stand; nobody sits |

Two screens carrying both a figure and a drill launch were split — one idea per screen, the way
P1–P7 already worked. 34 → 36 screens, minutes unchanged.

**Result, with the programme's 12/20 untouched:**

```
TRACK A   allocated  theory 480  practice 800  total 1280
          built      theory 480  practice 800  total 1280      exact

TRACK B   learner-active 985 of 1280 = 77 %   (target 80 %)
            within theory    258 / 480 = 54 %
            within practice  727 / 800 = 91 %
```

77 %, not 80. Reported, not faked. The remaining passive minutes are the module opener and the two
day-closing blocks. Every declared active minute is substantiated by the Trainee column of the
corresponding row in the instructor plan; if a row says "listens", the declaration is wrong.

---

## Validator state on ETPB3

| check | result |
|---|---|
| `check_balance.py` | 34 blocks — 0 failures, 0 warnings; Track A exact |
| `check_navigation.py` | 12 files — 0 failures, 0 warnings |
| `audit_ui.py` | 0 defects (2 drift notes: alpha scrims that are not flat colours) |
| `check_static.py all` | 0 findings |
| `check_visuals.py` | 0 failures, 10 warnings (design review, not mechanics) |
| `AuditDrive.run()` 1280 × 800 | **PASS** |
| `AuditDrive.run()` 800 × 1280 | **PASS** |
| `verify_figures.js` | 3/3 present, 0 console errors |

A clean run is not a pass. It means nothing mechanical is wrong.

---

## Untouched, as required

- GAS BASIC was read and served read-only; nothing under it was written.
- The Android application was not opened for writing.
- ETPB3 stays inside `factory-work/new course/`. Nothing was published to the tablets.
