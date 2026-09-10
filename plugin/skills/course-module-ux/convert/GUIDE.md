# Convert lane — off the chained multi-page model, onto one page

**v1 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this only when an existing module has to be brought onto the one-page architecture. If
you are building new, read `build/GUIDE.md` instead — you will never need most of what is
below, because it is about removing things.

**The content is not being rewritten.** The subject matter, the evidence and the citations stay
exactly as they are. This pass touches navigation, structure and wording only. If a conversion
tempts you to change what a page *claims*, stop: that is a content change and it needs the
course's own content skills, not this one.

Each step below is independently shippable, so a half-converted module still works.

---

## 0 · Three things the old model taught that are now defects

A next course will inherit modules built on the old chained model, and the old skill that
described it read as authoritative. These three patterns are **superseded** and must not
survive a conversion. Each was removed deliberately, and each has a reason that is not
aesthetic.

### (a) The hand-over chain — `id="gb-finish"` and `data-gbrun-to`

The old model had a deck's last slide hand over to the next artefact directly, so nobody had
to press Next on the runner. Delete those hooks. Two independent reasons:

1. They **advance a stored progress counter.** A page that declares a hand-over writes
   `step + 1`, so the counter moves for reasons that have nothing to do with the instructor
   finishing anything.
2. They **point the projector at a trainee's page.** The projecting device leaves the deck and
   lands on material written for a tablet in a trainee's hands.

On one page there is nothing to hand over *to*. The deck **announces** the next thing; it
never launches it.

### (b) "Repeat 2–3 per practical" — one runner step per practical

Practicals are now **screens inside the deck**, not steps in a runner. A practical that is a
runner step is a page the instructor navigates to, which is the thing the architecture removed.

This one was a **live bug found three times independently**: five practical/drill pages across
three modules still declared `GBRun({ ... next: ... })` after conversion. The engine documents
the consequence in its own source — a page declaring `next` **advances the module's stored step
counter merely by being opened.** So opening a practical write-up to look something up moved
the module on, and the next *Start module* opened the wrong step.

Grep for it and keep grepping:

```bash
grep -rn "next:\|finish:\s*true\|gb-finish\|data-gbrun-to" --include=*.html <module dir>
```

On a converted module the only surviving hits are the landing screen's own two-step
declaration. Everything else is a defect.

### (c) The way-back bar and the return bar on every page the runner opens

There is nothing to return **from** now. The delivery path never leaves the page, so a sticky
*"◀ Back to step 4 … Done — next step ▶"* bar is furniture that also carries the counter bug
in (a). Remove the bar and the `GBRun({key, total, label})` calls that rendered it.

A page that genuinely still exists outside delivery — a handout, a reference card, the
instructor's own record — keeps an ordinary footer link home. That is a link, not a bar, and it
writes nothing.

---

## 1 · The job has two phases, and doing only the first is the classic defect

Every conversion on this project moved a module's screen count **twice, weeks apart, for
different reasons**. Understanding that is understanding the whole job.

| | | Mod A | Mod B | Mod C | Mod D | Mod E |
|---|---|---|---|---|---|---|
| **Phase 1** | cut back to the architecture's own decision | 29 → **8** | 38 → **6** | 34 → **8** | 28 → **10** | not recorded |
| **Phase 2** | absorb the practicals into the deck | not recorded | 6 → **18** | 8 → **14** | 10 → **14** | → **12** |

So a module both **shrank and grew**, weeks apart. Every figure is a real count of
`<section class="slide">`: the phase-1 "before" column off the preserved pre-cut decks (29, 38,
34, 28) and the phase-2 "after" column off the delivered modules (18, 14, 14, 12). No file
counts, and the two blanks are gaps in the record rather than modules that skipped a phase.

**Phase 1 — delete the lecture the practical replaces.** A deck built for the old model taught
the subject *and* then sent everyone to a separate practical document that taught it again by
doing it. On one page that duplication is visible and indefensible, so the teaching screens the
practical supersedes come out.

**Phase 2 — absorb the practical's run into the deck.** The kit, the numbered steps, the abort
conditions, the marking and the debrief become screens.

**Doing only phase 1 leaves a module that skips its own content.** That is exactly the
90-minutes-missing defect: one module was **skipping 90 of its 220 minutes**, because two blocks
had been cut back in phase 1 and never absorbed in phase 2. Nobody noticed — the page looked
complete, and under the old model those blocks had their own pages that somebody was trusted to
open.

If you inherit a module that has had phase 1 and not phase 2, it will look **admirably compact**
and be broken. The tell is minutes, not screens: add up `data-mins` and compare against the
approved hours.

## 2 · So: count the blocks before you count anything else

Same order as building: the timetable first. List every block with its minutes, then ask of
each one **does it have a screen?** A block whose work lived on a separate page has no screen
by definition, and on one page that means it does not happen.

Present the inventory table from the router's gate and get it approved before writing markup.

---

## 3 · The conversion order

Doing these out of order wastes work — half the prose disappears with the sections it was in,
so trimming first is trimming twice.

**1 · Assets.** Copy `assets/gb_run.js` and `assets/gb_run.css` from this skill into the
module's own `assets/`. Do not carry forward an older copy: an old build script will not
rewrite JavaScript-held links and every step button 404s in the single-file package.

**2 · Fold every page into screens.** Practical write-ups, activity-launch pages, marking
pages, debrief notes, the module check. Use the kinds and the markup contract in
`build/knowledge/screen-kinds.json`. The check screen goes **last**.

**3 · Strip the chain.** Everything in §0. Then re-grep — do not trust yourself to have caught
them all.

**4 · Route every item by audience.** Run each item through
`build/knowledge/audience-split.json`. This is the pass that finds instructor cue text sitting
on a projected slide, which the old model tolerated because the projected slide and the
instructor's page were different files. On one page they are not.

Also strip internal codes from every visible `.slide-kind` line while keeping `data-block` in
the markup — the deep link and the generated run script both need it.

**5 · Kill every `<a href>` inside a slide.**

```bash
python measure/scripts/check_static.py slide-links <module page>
```

**6 · Collapse the runner to about two steps**, with real `mins:` on each. See
`build/GUIDE.md` §4.

**7 · Regenerate the instructor run script.** Every slide-number cross-reference in the
instructor's material is now wrong — see `runscript/GUIDE.md`. This is not optional
housekeeping: **96 slide-number references broke across two modules in one afternoon**, and the
instructor guide then told the instructor to announce the wrong task at three of five
activities.

**8 · Then, and only then, trim** to the budgets in `build/GUIDE.md` §7.

**9 · Measure.** `measure/GUIDE.md`, in full. A converted module that has not been measured on
a real viewport at a real settle time has not been converted; it has been edited.

---

## 4 · What not to do while converting

- Do not renumber, re-title or re-scope official topics, outcomes or hours.
- Do not paraphrase a quotation to fit a word budget. Quotations are exempt — say so in the
  delivery notes.
- Do not delete a safety-critical route because it looked like clutter. Router law 7.
- **Do not delete a form field.** Replacing a printed form with a digital one is the highest-risk
  moment in a conversion, and the losses are invisible to a line-level diff because what
  disappears is a *field*, not a paragraph. List every field with what it evidences, map each
  one, then sentence-diff. See `build/GUIDE.md` §8.
- Do not fix a shared stylesheet that other modules also load without saying so.
- Do not deploy. Build, report, hand over.

---

## 5 · Account for every deleted block

Before reporting a conversion done, diff the old pages against the new page and put **every**
deleted block into one of three buckets:

| Bucket | Meaning |
|---|---|
| **moved** | it is on a screen now — say which |
| **collapsed** | it is behind a `<details>` or in `data-cue` — say where |
| **deliberately cut and logged** | it had no job; the reason is in the delivery notes |

There is no fourth bucket. Anything that cannot be placed in one of these three is a loss, and
a loss that nobody wrote down is the failure mode this whole lane exists to prevent —
the clutter was visible and the loss is not.
