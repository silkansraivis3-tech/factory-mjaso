# Run-script lane — derive the instructor's running order, never type it

**v1 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this only when the task is producing or refreshing the instructor's running order for a
module page.

**Nobody hand-writes a slide number into instructor material.** Cutting or reordering a deck
silently invalidates every slide-number cross-reference. On one project **96 of them broke
across two modules in one afternoon**, and the instructor guide then told the instructor to
**announce the wrong task at three of five activities**. Nothing errored. Nothing looked wrong.
The instructor found out in the room.

So the running order is **derived from the deck's own markup** and regenerated after any deck
change.

---

## Run it

```bash
python runscript/scripts/gen_run_script.py <module page.html> \
       -o <instructor run script.md> \
       [--manifest <a file that knows the real activity codes>]...
```

| Exit | Means |
|---|---|
| `0` | written, clean |
| `1` | written, but there are findings a human has to close — they are also appended to the bottom of the generated file |
| `2` | usage or parse error, nothing written |

Run it, do not read it. It parses the page, groups screens into consecutive `data-block` runs,
and emits per screen: the number, the title, the kind, the activity code where there is one,
and the instructor's `data-cue` — labelled as **not on the screen**, so nobody reads a cue to
the room.

`--manifest` is repeatable and format-agnostic: point it at whatever file the tablet build uses
to know its tasks. Codes are matched as whole tokens, so decoration around them does not
matter.

---

## What it derives, and from what

The markup contract is in `build/knowledge/screen-kinds.json`. The generator reads
`data-block`, `data-kind`, `data-title`, `data-mins`, `data-activity` and `data-cue`, plus
`data-mins` on any element **inside** a slide, because a timer element commonly carries it
rather than the section.

Slide **order** gives the numbers; `data-block` gives the grouping. That split matters: the
numbers move whenever a screen is inserted, and `data-block` does not — so cross-references
elsewhere should quote the block, and only the generated file should quote numbers.

**The block-span line is the generator's own contribution.** After each launch it writes:

> The next 6 screens are the run of this block, screens 5–10. You do not leave the page — page
> through them where you stand.

A launch screen is normally at ceiling fill and cannot carry that line itself, and without it
an instructor goes looking for a separate document that no longer exists.

---

## Three traps, each of which produced silently wrong instructions

These are implemented in the script. They are written down here because the next person to
"improve" the generator will reintroduce them.

### 1 · The activity code must win over the slide kind

One module labels its task screens *"Real scenes then tablets"*, *"The person"*, *"Incident
analysis"* — while carrying the code. **Checking the kind first swallowed four of five tasks
into "just press Next."**

So: a code present means launch, full stop. The kind is consulted only when there is no code.

### 2 · A task manifest may decorate codes

Manifests carry entries like `T1 · marked` and `GAS701 · scored`. **Exact-matching a bare code
against those fails**, and the generator then tells the instructor to run a real tablet task
"in the room". Normalise before matching, and match as a whole token so `T1` does not hit
inside `T10`.

### 3 · Only read a code out of a title on a screen that is *already* a launch

Presentation screens titled *"P1 run · check and zero"* otherwise **invent eleven activities
that do not exist.**

The related failure is a launch-kind list that is too loose. An early version included the word
*drill*, which matched every screen that merely *described* a drill — six description screens
were each promoted to a launch and each had a code guessed off its title. `LAUNCH_KIND_WORDS`
in the script's CONFIG block is deliberately narrow for that reason. If you widen it, re-run
against a module you know and count the launches.

---

## Reading the findings

The generator is a linter as much as a generator. What it reports, and what each one usually
means:

| Finding | Usually means |
|---|---|
| activity X is not in any manifest supplied | it is a **room** activity, not a tablet one — or the code is wrong. Both are worth knowing; the generated line says "IN THE ROOM" so the instructor is not sent to a tablet |
| screen N is a launch with no code at all | the instructor cannot be told what to open. Add `data-activity` |
| no `data-activity`; code guessed from the title | works, but it is a guess. Add the attribute so it stops being one |
| N of M blocks declare no minutes | the printed total is short. A module with no minute total cannot be checked against its approved hours, and one that under-declares **hides missing work** — this is the same defect as the module that was skipping 90 of its 220 minutes |

Exit 1 is not a failure to fix by editing the generated file. Fix the **markup**, then
regenerate.

---

## After a deck change

Regenerate. Every time. Then check two things by eye, because they are the ones a diff hides:

1. The screen count in the header matches what you expect. A jump means a screen was
   duplicated by a copy-paste.
2. The block runs are contiguous. A block that appears twice in the output is a block whose
   screens are not adjacent, which is almost always an ordering mistake rather than a plan —
   the generator reports it as two separate runs rather than quietly merging them.
