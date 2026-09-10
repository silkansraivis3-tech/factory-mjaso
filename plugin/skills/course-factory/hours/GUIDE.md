# Hours — the accredited programme is law

**v1 (2026-09-07) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this in **plan** mode, or when auditing an existing course's time.
`knowledge/hours-rules.json` is the authority on every number and rule below — read it, and do
not restate its values here or anywhere else.

---

## Step 1 · Get the table out of the programme, not out of your head

The approved programme carries a topic/hours table. Find it and transcribe it whole — topic
number, title, theory hours, practical hours. Then **prove the transcription**:

> the sum of your transcribed theory and practical columns must equal the table's own
> `Total` row. If it does not, the transcription is wrong, not the table.

That assertion is in `scripts/check_hours.py` and it is the first thing it does. GAS BASIC's
table ends `35 | 8 | 43`, and a transcription that summed to 41 would have been silently believed
without the check.

Two traps, both real:

- **A docling-extracted table loses columns.** Rows where practical hours are zero can come out
  with the total sitting in the practical column. Read the `Total` row and reconcile; never take
  a single row's shape as the pattern.
- **The academic hour is not 60 minutes.** GAS BASIC's is 40. Read it from the programme. If the
  programme does not say, that is `UNKNOWN` and a blocking question — every number downstream is
  a multiple of it.

## Step 2 · Decide what sits outside the modules

Some topics are not module content. On GAS BASIC the final assessment (topic 23, 2 h) is separate
from every module check. List these at the gate explicitly, with the reason, so they are excluded
from the module budget on purpose rather than lost.

## Step 3 · Split topics into modules — the minutes decide, not the story

You may combine topics into a module freely; the programme does not mandate a module structure.
What it mandates is time. So:

1. assign topics to modules,
2. sum each module's allocated minutes from the programme,
3. **design inside that budget.**

The order matters. Designing the teaching first and totalling the minutes afterwards is exactly
how GAS BASIC ended up 33 % over, and the discovery came after all eight modules existed.

Sanity-check the day shape too: the programme's own timetable bounds it. If
`sum(all minutes) > days × slots_per_day × slot_min`, the course does not fit its accredited
days. That is a finding to report, not a rounding error to absorb.

## Step 4 · The overflow valve

Content that will not fit the minutes goes to the **handout, as self-study**. Not squeezed into
the block, not silently dropped.

Record every moved item — what it was, which topic it came from, how many minutes — in the
companion file. A trainee keeps the handout, so the content is still delivered; what changed is
that it is no longer claimed as class time it never had.

## Step 5 · The ratio, and the fallback that is mandatory

Target 80 % practical. Measure it on **allocated minutes**, not on how many activities exist.

Where the programme forbids it — GAS BASIC allocates 19 % practical, fixed by its own table —
the theory hours are **delivered as active learning**: a trainee activity inside the theory
block. A theory block with no trainee activity in it is a defect in this system, and that is the
rule the 80/20 target degrades into, not an excuse to stop trying.

Record the achieved ratio and the reason it is below target.

## Step 6 · ILOs

Main ILOs and the study programme are copied verbatim. Sub-ILOs may be re-expressed to make a
topic digital or practical — mark each one `PROVISIONAL` until the owner ratifies it, and never
renumber it anywhere a trainee can see. IMO model courses are guidance; the programme governs.

Wording, verbs and constructive alignment are `novikontas-pedagogy-toolkit`'s — point at it.

---

## The check

```bash
python hours/scripts/check_hours.py --spec COURSE_START.json
python hours/scripts/check_hours.py --programme prog.json --plan plan.json   # before COURSE_START exists
```

It exits non-zero when the transcription does not reconcile, when any module's built minutes do
not equal its allocated minutes, or when the total will not fit the accredited days. Read the
per-module lines, not just the exit code — a module that is under is as wrong as one that is over,
and only the lines say which.

Write the result into `COURSE_START.json`'s additive `hours` block (shape in
`knowledge/hours-rules.json`). That block is this skill's contribution to a contract that has no
notion of time; do not alter the rest of the schema, which `novikontas-course-start` owns.

## What "done" looks like

- the transcribed table reconciles with the programme's own total row
- every module's built minutes equal its allocated minutes, exactly
- outside-module topics listed with reasons
- the whole course fits the accredited days
- achieved practical ratio recorded, with the active-learning fallback named where it applies
- every moved-to-handout item recorded
- every re-expressed Sub-ILO marked `PROVISIONAL`
- one plan document per module, stating its own allocated and built minutes on its face
