# Phase 4C — the canonical composition system

Plugin **2.3.0**. Phase 4B extracted the shell. That was necessary and not sufficient: ETPB3 then
passed every check it had — no spill, no collisions, contrast fine, tap sizes fine, "screen fill"
90 % — while putting a small cluster of content in the corner of a large empty panel.

**The fill number was measuring the box.** A big empty container is not a composition.

---

## What GAS BASIC actually is to a new course

Not a template for the *course*: not its module count, screen count, hours, theory/practice split,
topics, ILOs, activity count or sequence. Those stay course-specific, and 2.3.0 hard-codes none of
them — a module may be 5 screens or 60.

It **is** the master for the *product*: visual design, presentation UX and UI, composition,
navigation, interaction feel, spacing, typography, hierarchy, full-screen behaviour, activity
launch, feedback, task-page identity, tablet behaviour, polish.

> GAS BASIC design system + new course content + new course-specific technical visuals.

---

## 1 · The composition vocabulary — `templates/gb_compose.css`

Studied across Module_01, 03, 04, 07 and 08, the golden deck turns out to carry a small, stable
set of compositions, each applied to `.slide-body`:

| composition | golden usage | what it is for |
|---|---|---|
| `opener` | covers, block openers | one statement, centred, deliberately spare |
| *(flow)* | ordinary screens | lead → cards → takeaway |
| `two-col` (+`wide-left`/`wide-right`) | explanation beside a visual | the workhorse; the thing that stops a figure being adrift in a wide screen |
| `stage` (`exp-stage`, `fig-stage`, `lad-stage`, `xs-stage`) | one dominant teaching visual | the drawing is `flex:1` and eats what the caption and controls leave |
| `activity` | every activity launch | centred, code dominant, nothing clickable |
| `checkbody` + `bigcall`/`bigq` | knowledge check | one big question |
| `sum` | closing grid | one column per block |
| `trio`, `photo-wrap`/`scrim`/`copy`/`badge` | photographs | full bleed, copy on a scrim |

Every one shares a single mechanic, and it is the whole point:

> **The composition claims the stage.** `flex:1`, `min-height:0`, content placed deliberately —
> centred, split or filled. Nothing is left where the normal flow happened to drop it.

`gb_shell.css` was split so the two have one owner each and **no rule appears in both** (verified
mechanically): the shell decides what a screen *is*; `gb_compose.css` decides what goes *on* it.
A course's own CSS should now contain only its technical drawings, genuinely unique mechanics, and
documented exceptions.

## 2 · Composition QA — `measure/scripts/audit_compose.js`

Measures **meaningful content** — headings, copy, list items, table cells, svg, img, canvas,
controls — and ignores the div, panel or card holding them. Furniture inherits its right to the
space from what it contains.

Reports `ink`, `centroid`, dead halves (the corner-cluster detector), `focal`/`focalW`, and a
verdict. Two calibrations, both learned by being wrong first:

- **Vertical drift is what the eye notices.** The first version checked only x, and a deck whose
  content stopped at 60 % of every screen passed it.
- **Area alone is a landscape assumption.** A wide drawing at the full width of an 800 × 1280
  portrait screen covers 20 % of its area and is using the screen as well as it can. A figure is
  undersized only when it is small in its *own dominant axis* too.

Not a percentage law. A WEAK verdict is a defect; a REVIEW asks a human to look. **Choosing a named
composition counts as declaring intent** — an activity announcement that tiled the screen with text
would be the defect — and `data-compose="sparse"` declares it for a flow screen. The balance and
dead-half checks apply to everything regardless.

Recorded as **L17** in `FACTORY_LAWS.md`.

---

## 3 · ETPB3 — the composition pass

All 38 screens reviewed at 1280 × 800 on a contact sheet (`_work/contact_sheet.html`, real markup
and real stylesheets, paginated) and then individually.

**Activity launch — the owner's specific complaint.** Was: a navy card, left-aligned, floating in a
light slide with two thirds empty. Now the golden treatment, verbatim: the whole screen is
`.slide.dark.activity`, the body centred, the code set at `clamp(38px,9vmin,110px)` in amber as the
dominant focal element, title and instruction beneath, three `.act-step` blocks carrying the task's
**real parts** (condensed from the practical cards, nothing invented to fill space), and the
announcement line last. All 17 converted. Median screen fill across the module went **68 % → 90 %**,
and the centroid of every launch screen is now x ≈ 0.50.

**Star/delta — preserved and enlarged.** Interaction and teaching logic untouched: six steps, the
supply never moves, only the bridges change. Put on `stage`; the terminal board went from
**1131 × 300 to 1146 × 355** and its focal share from **0.33 to 0.72**. It is the visual centre of
its screen.

**Screens repaired: 13.**

| screen | was | now |
|---|---|---|
| module opener | cover and orientation on one screen | split: `opener` with the question held, then the orientation screen — the golden's own pattern, and the instructor cue had always said to open with a question the screen never showed |
| Kā rodas griezes moments | square figure alone on a stage, 490 px wide in a 1146 px screen | `two-col`, visual **left** (the chrome lives bottom-right and the component's control row kept reaching it), the explanation it never had on the right |
| Datu plāksnīte, Zvaigzne un trijstūris | figure sharing a flow body | `stage` |
| Rotējošās un statiskās | lead + 2 cards | `two-col` — statement and support beside what the instructor listens for |
| Galvenie parametri | six cards | a **table** — a list of values is a table |
| Darba vieta un drošība | lead + 3 cards | `two-col wide-left` |
| Pieslēgšanas darbu secība | six steps in one narrow column | `two-col wide-left` — the sequence beside *why* that sequence |
| Kas jāpārbauda pirms sprieguma | six steps in one narrow column | `two-col wide-left` |
| Motora aizsardzības | lead + 2 cards | `two-col` |
| Kas ir atbilstība | lead + 2 cards | statement + support + takeaway |
| Dienas noslēgums (B4) | 41 words | `sum` — what each block left behind |
| Dienas noslēgums (C4), **45 min** | two cards, 35 words | `two-col wide-left` — the board they fill in, and what counts as an explanation |
| Noslēgums un nodošana | 59 words | `sum` — the six outcomes, named |

Composition mix went from *flow 14 / activity 17 / stage 3 / sum 2 / opener 1* to
**flow 9 / two-col 7 / activity 17 / stage 2 / sum 2 / opener 1**.

### Defects found by looking, not by counting

- **`.fill` silently disabled the figure cap.** `max-height:100%` inside a grid column with
  content-based height has nothing to resolve against; `min(100%, var(--fig-max))` gave up
  entirely and a figure grew 45 px past the screen with its controls under the chrome. The cap is
  one knob; it is now the only one.
- **`min-height:0` on body children is exactly wrong.** A shrunk mount keeps painting at full size
  — measured as a 1153 × 125 px overlap of a figure on the card below it.
- **A fragment header comment is a landmine.** `Mount into <div id="f1-lauks">` inside a comment
  matched a regex before the real mount did, split the comment open, and printed its body on the
  slide. Every check stayed green because the component still rendered underneath.
  `verify_figures.js` now fails a mount containing loose text, and the fragment headers name a
  selector (`#f1-lauks`) rather than a tag.
- **The contact sheet lied about four screens** until it loaded the module's own `<style>`; the
  technical drawings rendered as black boxes. A review tool that misrepresents the thing under
  review is worse than no tool.

---

## Validator state

| check | 1280 × 800 | 800 × 1280 |
|---|---|---|
| `AuditCompose.run()` | **COMPOSED** 38/38, 0 weak, 0 review | **COMPOSED** 38/38 |
| `AuditDrive.run()` | **PASS** — 0 low, small, spill, tap, collide | **PASS**, no horizontal scroll |
| `GBVerifyFigures.run()` | **PASS** 3/3, 0 console errors | — |
| `check_balance.py` | 34 blocks, 0 failures — **480 / 800 exact** | |
| `check_navigation.py` | 12 files, 0 failures, 0 warnings | |
| `audit_ui.py` | 0 defects | |
| `check_static.py all` | 0 findings — **0 links inside slides** | |

38 screens, **1280 minutes**, Track B unchanged at 77 % learner-active.

Every Phase 4B protection still holds: touch navigation, runtime figure checks, exact Track A
hours, the Track B metric, no links inside slides, strict plugin validation, and a version bump for
every content release.

## Untouched

GAS BASIC was read and served read-only. The Android application was not opened for writing. ETPB3
stays inside `factory-work/new course/`.
