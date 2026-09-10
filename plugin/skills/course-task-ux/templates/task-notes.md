# Task screen notes — <course / module>

**Written by the skill during the run, not afterwards.** It exists so the next person — who
may be a session with no memory of any of this — can pick the tasks up cold and know what is
finished, what is guessed, and what still has to be checked by a human.

Fill every section. "None" is a valid and useful answer; a blank is not.

---

## 1 · What was produced

| # | Task | Answer mechanic | Parts | Typed input | Engines loaded | File |
|---|---|---|---|---|---|---|

This should match the plan table that was approved at the gate. **If it does not, say what
changed and why** — an approved mechanic that quietly became a different mechanic is the
single most expensive thing to discover late.

## 2 · Numbers a record asks for (SKILL.md §10)

| Record field | Asked of | Rendered on screen where | Verified |
|---|---|---|---|

One row per number any record sheet, register or assessment form asks for. "Rendered where"
must name the element, not the calculation. A row with no rendering location is a defect, not
a note.

## 3 · Markers

Every marker written into any task page or its content, with its source. Nothing is used and
left unreported.

| Marker | Where | What it stands for | What would resolve it |
|---|---|---|---|
| `UNKNOWN` | | asked, the owner did not know | |
| `PLACEHOLDER` | | structure right, content missing | |
| `PROVISIONAL` | | built but depends on something unapproved | |
| `[VERIFY: …]` | | asserted from an unconfirmed source | |

Photograph licences, regulatory references and answer keys are never invented — if one is
missing it is a marker here, not a plausible guess in the page.

## 4 · Verification actually performed

| Check | How | Result |
|---|---|---|
| `check_task_pages.py` — syntax | | |
| `check_task_pages.py` — deadmarkup | | |
| `check_task_pages.py` — numbers | | |
| `check_task_pages.py` — floor | | |
| `check_task_pages.py` — kbd | | |
| Console read after every scripted edit (§12) | | |
| `measure_in_page.js` at target viewport | viewport measured: | |
| Task driven to its completion panel (§9) | | |
| Keyboard escape, steps 1–7 of `references/typed-input.md` | | |

State the viewport you measured at and how many nodes were examined. A report saying "no
violations" without saying what it looked at cannot be told apart from one taken in a 0 × 0
pane. **If `node` was absent, the syntax check exited 3 — say so and say that the browser
console was read instead.**

## 5 · Cross-module drift (SKILL.md §14)

Any engine or stylesheet fix applied to some modules and not others, with the reason. An
undocumented drift becomes a mystery bug; a documented one is a decision.

| File | Applied to | Not applied to | Why |
|---|---|---|---|

## 6 · Content left alone

Anything that looked like a content error and was **not** changed, per SKILL.md §14. Wording,
values, units, terminology, citations. Report it here as `[VERIFY: …]` for the owner rather
than fixing it.

## 7 · Open, and what would close it

The honest list. What is not finished, what could not be verified in the session, and
specifically **what would verify it** — a device to test on, a record sheet to read, an
answer key to approve.

## 8 · Feedback on this skill

The only channel through which real delivery reaches the standard. Read at the next revision.

- Rules that were **wrong** — a rule this skill states that the pages that actually shipped
  and worked do not follow. Per SKILL.md §13 that means the skill is the defect.
- Rules that were **missing** — a defect hit during this run that the skill does not cover.
- Rules that **cost time without earning it**.
- Anything in the bundle that was read and turned out not to be needed for this mode.
