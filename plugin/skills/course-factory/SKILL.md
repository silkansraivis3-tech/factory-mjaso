---
name: course-factory
description: >
  Use for a WHOLE accredited course on the NOVIKONTAS tablets - building one from an approved
  programme, or UPGRADING an existing one. Trigger on "make a new course", "build course X like
  GAS BASIC", "add a course to the tablets", "how many hours does this module get", "is this 1:1
  with the programme"; and equally on RETROFIT requests about material that already exists:
  "redesign Module 1 using the Course Factory", "upgrade this existing module", "make my existing
  module like GAS BASIC", "make these modules presentable", "make this module production-ready",
  "improve the existing presentation / course UX", "modernise this existing course", "apply Course
  Factory to this module", "make this module more visual and interactive", or the same intent in
  Latvian or Russian. In retrofit the course CONTENT is locked and the existing DELIVERY
  implementation is not - screens, layout, visuals, animation and interaction are rebuilt to the
  canonical product, and the operator never has to name a skill, a validator or a folder. Owns
  mode selection, the accredited-hours law, ILO immutability, the content-lock/delivery-freedom
  law, COURSE_LANGUAGE, and the contract for adding a course to both terminals. NOT the deck's
  screen craft (course-module-ux), NOT the visual layer (course-module-ui), NOT what representation
  teaches a concept (course-visuals), NOT trainee task screens (course-task-ux), and never what a
  course teaches.
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
| **retrofit** | upgrade, redesign, modernise or "make presentable" material that **already exists** | `retrofit/GUIDE.md` |
| **restyle** | make one **narrow** cosmetic change and nothing else | `retrofit/knowledge/routing.json` § restyle |
| **ship** | put a built course onto the trainee and instructor terminals | `tablet/GUIDE.md` |
| **audit** | check an existing course against the programme and the terminals | `coverage/GUIDE.md`, then both lanes' verify sections |

`retrofit/knowledge/routing.json` is the authority on which mode a free-form request selects, and
on telling **retrofit** apart from **restyle**. Match the operator's *intent*, never a phrase — a
colleague in Cowork types "Redesign Module 1 using the NOVIKONTAS Course Factory" and that has to
be enough, with no skill name, validator name, folder path or git in it.

Restyle needs **both** a narrow cosmetic target *and* a scope limiter: "only change the colours" is
a restyle; "change the colours and make it like GAS BASIC" is a retrofit. When someone asks for a
restyle, give them a restyle — say in one line what a full retrofit would additionally do, and
stop. Doing more than was asked is not generosity.

Never load a lane the mode does not need. `hours/` answers "how long may this be"; `tablet/`
answers "where does it live and how is it wired"; `coverage/` answers "is everything the programme
**and the model course** ask for actually taught"; `retrofit/` answers "what of this existing
module survives, and what gets rebuilt". They never run together — except that a retrofit still
obeys the hours law, so `retrofit/` reads `hours/` for Track A and nothing else.

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

## The six laws

These are not preferences. Each one is here because breaking it cost real rework — the first four
on GAS BASIC, the last two on the first two real pilots.

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

### 3 · Two tracks, and only one of them is yours

This is one rule that reads like two numbers, and the ETPB3 pilot got it wrong by treating them
as the same number. Keep them apart.

**Track A — the allocation.** The approved programme says how many academic hours are theory and
how many are practice. That is external, auditable and **not editable**. Your job is that the
module as *built* claims those same minutes against those same buckets: a module claiming 20
practice hours puts 800 minutes of trainee practice in front of the room. ETPB3 built 650 theory
/ 630 practice against an allocated 480 / 800 and nothing caught it, because `check_hours.py`
only compares the **total**. A total-only check cannot see a bucket swap. Declare the bucket per
block with `data-track` and run `check_balance.py`.

**Track B — the delivery modality.** Of the minutes in front of the room, how many have the
trainee *doing, deciding, producing or saying* something, and how many have them receiving? This
is a **design metric**. It changes nothing in Track A — a theory-allocated minute delivered as an
activity is still a theory minute. Declare it per block with `data-active`.

**The 80 % target belongs to Track B.** Aim for 80 % of class minutes learner-active. Where the
programme makes the *practical* share small — GAS BASIC allocates 8 practical hours of 43 — the
answer is not to give up but to make the theory hours active:

> the theory hours are **delivered as active learning** — a tablet task inside the theory block,
> not a longer lecture.

Mandatory, not optional. A theory block with no trainee activity in it is a defect.

Record both figures in the companion file with the reason for any shortfall. **Do not reach the
target by renaming screens.** `check_balance.py` rejects the three ways people try: an active
count above the block's own minutes, a practice block whose room is receiving for most of it, and
a theory block claiming 100 % active — somebody has to set the task.

### 4 · Nothing is useless until you have grepped for what depends on it

Before removing any control, label, field or file: grep its id, class, label and filename across
**both terminals, the course tree and every generated script**. On GAS BASIC, three of four
"useless" findings were load-bearing — timer buttons the instructor run script tells the
instructor to press, print buttons on hand-out documents, and hrefless `<span id="gb-home">`
elements that are how a page declares it has no way back. Unused today is not useless: data a
planned system will read is not dead.

### 5 · Content is locked. The delivery implementation is not.

> **PRESERVE THE COURSE CONTENT. DO NOT PRESERVE THE EXISTING DELIVERY IMPLEMENTATION BY DEFAULT.**

`retrofit/knowledge/content-lock.json` is the authority — read it, do not restate it.

**Locked**, needing explicit authorisation: technical meaning, programme requirements, ILOs and
Sub-ILOs, official hours, assessment intent, intended practical exercises, course terminology,
source-supported facts, COURSE_LANGUAGE.

**Free**, redesign on the evidence without asking: screen count, screen order, HTML structure,
layouts, card arrangements, density, progressive disclosure, visual implementation, animation,
interactive mechanics, task presentation, navigation, CSS/JS, hierarchy, composition.

**What this law is for.** A colleague asked for an existing module to be brought up to GAS BASIC
quality and got back a technically correct retrofit that still felt weaker than GAS BASIC — because
Claude treated the existing HTML as something to preserve. Conservatism looks like diligence.
Keeping a layout feels safer than replacing it, every single decision to keep something is
defensible, and the sum of them is a module that passes every check and is not the product. **The
existing module is source material plus learning intent, not the presentation template**, and "the
HTML works" is not an argument for keeping it.

An existing visual is *evidence of a teaching decision*: preserve the decision, rebuild the
implementation. The star/delta figure's claim — the supply never moves, only the bridges change —
survives; its small SVG does not have to.

### 6 · COURSE_LANGUAGE is declared, and the operator's language is not it

Mandatory in **plan** and **retrofit** alike. Detect it from the authoritative course-facing
material, state it back in one line, and lock it.

Course-facing — slides, tasks, handout, assessment, feedback, instructor cues, practical cards,
START_HERE, the run script — stays in COURSE_LANGUAGE unless translation is **explicitly**
requested. The chat report, `factory-notes.md`, code comments and validator output follow the
operator.

A Latvian operator asking, in Latvian, to redesign an English module gets a Latvian report and an
English module. Translating an accredited artefact because the request arrived in another language
destroys it, and it happens one screen at a time. `retrofit/scripts/check_language.py` is the
drift check.

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
   checks and the provenance record. Then, in the page, `GBVerifyFigures.run()` and
   `await GBVerifyFigures.motion()` — every figure rendered, and every figure alive rather
   than a picture (L20). Then `course-visuals/review/GUIDE.md`, which asks the question
   no script can: **does this visual actually teach?** Nothing at `RIGHTS_REVIEW_REQUIRED` may ship.
9. `course-module-ui/scripts/audit_ui.py --strict` over a **new** module's stylesheets — the
   visual sign-off. `--strict` is right for new work and wrong for shipped material: never point
   it at a delivered GAS BASIC or Electrical Technician module. Those carry known drift that
   `course-module-ui` records by name; **report drift, do not repaint a signed-off deck.** The
   point is that new work does not start a second visual dialect.

(2) and (5) exist because (1), (3), (4) and (6) all passed on a course that was missing an
accredited outcome and shipping a dead section. **Every check here was added after something got
through the others.**

10. **In retrofit only** — `retrofit/scripts/check_language.py <course> --declare <LANG>` (the
    course did not change language), and `retrofit/scripts/classify_module.py` **again**. A
    retrofit that started at C and still classifies C has not finished.

Then write `templates/factory-notes.md` into the course folder: what was produced, every marker
with its source, the achieved ratio, what was moved to the handout and why, and a final section
of **feedback on this skill**. That last section is the only channel through which real use
reaches the skill — it is written by this skill during the run, never left for a human.
