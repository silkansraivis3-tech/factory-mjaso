---
name: course-factory
description: >
  Use when someone asks for a WHOLE accredited course to be built, converted or signed off as
  the GAS BASIC system: one-page HTML modules an instructor drives with Next, interactive
  trainee tasks, a handout, a final assessment, and both Android tablet terminals. Owns the
  build order, the accredited-hours law (minutes must match the approved programme exactly),
  the ILO immutability rule, the 80/20-or-active-learning rule, and the contract for adding a
  course to the two terminals without touching app code. Trigger on "make a new course",
  "build course X like GAS BASIC", "add a course to the tablets", "how many hours does this
  module get", "is this 1:1 with the programme", "course data pack", or a typed course brief.
  Course-agnostic and delivery-target specific. NOT the deck's screen craft (course-module-ux),
  NOT the module's visual layer (course-module-ui), NOT trainee task screens (course-task-ux),
  NOT Word/pptx artefacts or intake (the novikontas-* family), and never what a course teaches.
---

# Course factory — an accredited programme becomes two tablets

**v1.1 (2026-09-10) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

**The acceptance test.** Someone who has never seen the course opens the instructor terminal,
types their ID, picks the module, presses **Start**, and presses **Next** to the end — and a real
accredited class gets taught, in the minutes the approved programme allows, with the trainees'
tablets carrying every task the screens announce.

This skill is the **entry point** for that delivery target. It decides mode, runs the gate, and
routes. It does not itself write screens, tasks, or content.

---

## Mode first, then read one lane

| Mode | You are asked to | Read |
|---|---|---|
| **plan** | turn an accredited programme into a module set with hours that add up | `hours/GUIDE.md` |
| **ship** | put a built course onto the trainee and instructor terminals | `tablet/GUIDE.md` |
| **audit** | check an existing course against the programme and the terminals | `coverage/GUIDE.md`, then both lanes' verify sections |

Never load a lane the mode does not need. `hours/` answers "how long may this be"; `tablet/`
answers "where does it live and how is it wired"; `coverage/` answers "is everything the programme
**and the model course** ask for actually taught". They never run together.

`coverage/` exists because the other two cannot see its failure. A course can have exact hours and
perfect wiring and still not teach an outcome. On GAS BASIC the topic-level record was green at
64 of 64 and had never once been checked against the model course's own 266 itemised outcomes —
where one real gap was waiting.

### Deliberately outside this bundle — point at these, never copy them

| Concern | Owned by |
|---|---|
| Screen craft, one-page architecture, deck measurement, run-script generation | `course-module-ux` |
| **The visual layer** — palette, typography, light/dark-photo modes, header band, cards, pills, takeaway, semantic status colour | **`course-module-ui`** |
| **What representation teaches a concept** — photo, schematic, animation, chart, cutaway, or no visual at all; the asset pipeline, provenance and rights | **`course-visuals`** |
| Trainee task screens — answering, navigation, typed input, completion | `course-task-ux` |
| Publishing a finished course to the two terminals and the shared repository | `course-tablet-publisher` |
| Course intake — course type, accreditation, equipment, regulations | `novikontas-course-intake` |
| The course plan document, competence matrix, session plan | `novikontas-course-plan` |
| `COURSE_START.json` contract, honesty markers, traceability tiers, gap report | `novikontas-course-start` |
| ILO wording, verbs, constructive alignment, assessment design | `novikontas-pedagogy-toolkit` |
| Exercise forms, handouts, written tests, decks as pptx | the `novikontas-*` material skills |
| Visual identity — logo, colour, type | `novikontas-brandbook` |
| Getting text and figures out of source PDFs | the project's own docling knowledge base |

If a question belongs to a row above, say so and point. Do not re-derive it here.

### When an organisation skill is not installed

The `novikontas-*` skills are **not** part of this plugin and are not guaranteed to be present.
Owner decision **D-3**: use the organisation skill when it is installed; otherwise use the minimal
fallback in **`org/ORG_DEPENDENCIES.md`**; either way record which route was taken in
`factory-notes.md` §0.

Three are **blocking** — `novikontas-pedagogy-toolkit`, `novikontas-handouts` and
`novikontas-course-start` own required build steps and have a fallback each. The rest are pointer
rows: name the skill that would have owned the question, answer it within this factory's own rules,
and say so. Never paraphrase an absent organisation skill from memory and present it as its content.

---

## The brief — what the operator types, and what you must not ask

The operator types free-form. Extract these; **ask only for what is genuinely absent**, batched
2–4 at a time:

1. **Which accredited programme governs** — the approved document, by name or path. Without it
   there is no hours law and no ILOs, so this is the one blocking question.
2. **The knowledge base** — the docling-extracted sources for the subject.
3. **What is different from GAS BASIC** — simulator? live-fire facility? group size? days?

Never ask: the module split, the screen count, the task codes, the pass marks, or the file
layout. Those are **derived**, and deriving them is this skill's job. Never web-search during
intake — not in the brief, programme or knowledge base means `UNKNOWN`.

---

## The four laws

These are not preferences. Each one is here because breaking it cost real rework on GAS BASIC.

### 1 · The approved programme is law, and minutes are the law's units

`hours/knowledge/hours-rules.json` is the authority — read it, do not restate it. The short form:

- An academic hour is whatever the programme says it is (GAS BASIC: **40 min**). Never assume 60.
- Every module's built teaching time must equal its allocated minutes **exactly**.
- Anything that will not fit becomes **self-study in the handout**. The handout is the overflow
  valve; class time is fixed. *(Owner's ruling, 2026-09-07.)*
- Run `hours/scripts/check_hours.py` before believing any plan. It exits non-zero when the sum
  is wrong, and it is the gate.

**What this law is for.** GAS BASIC was built to 2175 minutes against an accredited 1640 — a
33 % overrun discovered only after all eight modules existed, because nothing counted minutes
until someone thought to. The contract that orders the whole course factory
(`COURSE_START.json`) has **no hours field at all**. This lane adds one.

### 2 · Main ILOs are untouchable

Main ILOs and the approved study programme are copied **verbatim** and never edited, renumbered
or "improved". Sub-ILOs **may** be re-expressed to make a topic digital or practical — that is
the point of the exercise — but:

- a re-expressed Sub-ILO is marked `PROVISIONAL` until the owner ratifies it, and
- it is **never renumbered in anything a trainee sees**.

IMO model courses are **guidance**; the approved programme **governs**. Where they disagree, the
programme wins and the model course is cited as support, never as authority.

### 3 · 80/20 practical, or active learning instead

Aim for 80 % practical / 20 % theory. On an accredited programme this is often **arithmetically
impossible** — GAS BASIC allocates 8 practical hours of 43, i.e. 19 %, fixed by the programme's
own table. When the split cannot be reached:

> the theory hours are **delivered as active learning** — a tablet task inside the theory block,
> not a longer lecture.

That is the fallback, and it is mandatory, not optional. A theory block with no trainee activity
in it is a defect in this system. Record the achieved ratio in the companion file with the reason.

### 4 · Nothing is useless until you have grepped for what depends on it

Before removing any control, label, field or file: grep its id, class, label and filename across
**both terminals, the course tree and every generated script**. On GAS BASIC, three of four
"useless" findings were load-bearing — timer buttons the instructor run script tells the
instructor to press, print buttons on hand-out documents, and hrefless `<span id="gb-home">`
elements that are how a page declares it has no way back. Unused today is not useless: data a
planned system will read is not dead.

---

## The gate — approved before anything is built

Changing a table row is free. Changing eight built modules is not. Present this and **stop**:

| | |
|---|---|
| **Programme** | document, edition, academic-hour length, total hours (theory / practical) |
| **Module split** | module → topic numbers → allocated minutes, with the column summing to the programme total |
| **Ratio** | practical % achieved, and if under target, where active learning carries the theory |
| **Per module** | screen count, task codes, what the module check is, whether a practical needs a facility |
| **Markers** | every `UNKNOWN`, `PLACEHOLDER`, `PROVISIONAL`, `[VERIFY: …]` raised so far |

Nothing is built until the operator approves that table. The module split and the minutes are
the expensive things to get wrong.

---

## Build order

`knowledge/build-order.json` is the authority. Read it; it names the owning skill for each step
and what each step must not start without.

The shape, for orientation only: programme → hours → module split → **gate** → ILO map →
per-module screen inventory → **visual system** → tasks → screens → handout → assessment →
module plans → terminals → verify.

Three orderings that are not negotiable, all three learned by getting them wrong:

- **Screen inventory before any screen exists.** `course-module-ux` owns that gate.
- **The visual system before any screen exists.** `course-module-ui` owns it, and for a new
  module it is a **required** step, not an optional polish pass — see below.
- **Task pages before the deck announces them.** A screen that announces `T3` when the tablet
  has no `T3` is the worst failure in the room, and it is only caught by the three-way
  cross-check in `tablet/`.

### The visual layer is routed, never improvised

When a new module reaches visual production, **route it to `course-module-ui`**. That skill is
the authority on the look; this one does not restate a single colour, radius or component rule,
and neither should you. It carries `knowledge/tokens.json` (the values),
`templates/gb_tokens.css` (paste, do not retype) and `references/anatomy.md` (the components).

GAS BASIC **Module_01 is the canonical visual reference** — the palette, the typography, the
light and dark/photo modes, the header band, card geometry, pills, spacing, radius, shadow, the
takeaway treatment, the semantic status colours. It is *not* a template to copy:

- **There is no canonical screen count.** Screens are derived from the learning need, the
  delivery method, the content depth and the practical work. Ten screens, twenty-five, fifty,
  almost no presentation, practical-only — all legitimate. Never add filler screens to resemble
  Module_01 numerically, and never cut real teaching to resemble it either.
- **Not every screen has to be interactive**, and low visible density is not low learning depth.
  Progressive disclosure, layered cards, diagrams and interactive figures teach without a wall
  of text. Compact (`course-module-ux` law 3) never means thin.
- What must match is the **system**: visual language, UI quality, UX behaviour, tablet-first
  delivery, the Start → Next → Next one-page model where it applies, component styling,
  responsive behaviour, visual hierarchy, task usability and functional quality.

`build-order.json` step 8 is the contract; `no_fixed_slide_count` and `density_is_not_depth` in
that file are the rules above in their authoritative form.

---

## Honesty markers

One set, identical to the rest of the family (`novikontas-course-start` owns the definitions):

| Marker | Means |
|---|---|
| `UNKNOWN` | Asked, operator did not know. Record that it was asked. |
| `PLACEHOLDER` | Structure right, real content missing. |
| `PROVISIONAL` | Content exists but depends on something unapproved — every re-expressed Sub-ILO, every pass mark not yet ratified. |
| `[VERIFY: <what to check>]` | Asserted from a source this skill could not confirm. Always carries its payload. |

Never invent regulatory content, hours, pass marks or citations. Every marker must appear in the
companion file — a marker used and never reported is the failure this rule exists to stop.

---

## Verify before reporting done

Run these, read the output, then report. A green exit is not proof the work happened — inspect
the line for the thing you changed.

1. `hours/scripts/check_hours.py` — minutes match the programme
2. `coverage/scripts/check_syllabus_coverage.py` — every **itemised outcome** of the model course
   is taught. Not the same question as the topic record, and it found the only real content gap in
   266 outcomes on a course whose topic record was already green.
3. `tablet/scripts/verify_course.py` — structure, counts, check→hand-off order
4. `tablet/scripts/verify_links.py` — every link resolves in the **merged** asset root
5. `tablet/scripts/audit_navigation.py` — every page is **reachable** and has a way back. Not the
   same question as (4): a section whose own index nothing links is invisible in the built app
   however good its links are. That was 28 pages on GAS BASIC — every safety brief, rotation plan
   and practical write-up — with `verify_links.py` green.
6. `tablet/scripts/crosscheck_tasks.py` — deck ↔ run script ↔ tablet manifest agree
7. `course-module-ux`'s measurement lane for the screens themselves
8. `course-visuals/scripts/check_visuals.py` and `check_assets.py` — the deterministic visual
   checks and the provenance record. Then `course-visuals/review/GUIDE.md`, which asks the question
   no script can: **does this visual actually teach?** Nothing at `RIGHTS_REVIEW_REQUIRED` may ship.
9. `course-module-ui/scripts/audit_ui.py --strict` over a **new** module's stylesheets — the
   visual sign-off. `--strict` is right for new work and wrong for shipped material: never point
   it at a delivered GAS BASIC or Electrical Technician module. Those carry known drift that
   `course-module-ui` records by name; **report drift, do not repaint a signed-off deck.** The
   point is that new work does not start a second visual dialect.

(2) and (5) exist because (1), (3), (4) and (6) all passed on a course that was missing an
accredited outcome and shipping a dead section. **Every check here was added after something got
through the others.**

Then write `templates/factory-notes.md` into the course folder: what was produced, every marker
with its source, the achieved ratio, what was moved to the handout and why, and a final section
of **feedback on this skill**. That last section is the only channel through which real use
reaches the skill — it is written by this skill during the run, never left for a human.
