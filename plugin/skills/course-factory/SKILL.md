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

**v1.2 (2026-09-30) · Maintained by Raivis · part of the `course-factory` plugin, shared with colleagues through the marketplace**

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
| **preview** | let a colleague SEE the course — "how does it look", "let me review it", "open it in the browser" | `course-tablet-publisher` → `references/preview-and-approval.md` |
| **restyle** | make one **narrow** cosmetic change and nothing else | `retrofit/knowledge/routing.json` § restyle |
| **ship** | put an **approved** course onto the trainee and instructor terminals | `tablet/GUIDE.md`, and `course-tablet-publisher` owns the act |
| **audit** | check an existing course against the programme and the terminals | `coverage/GUIDE.md`, then both lanes' verify sections |
| **orchestrate** | build a WHOLE course from a knowledge base, with one agent per module | `orchestration/GUIDE.md` |

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

`orchestration/` is the only lane that is about the *run* rather than the course, and `coverage/`
exists because exact hours and perfect wiring still cannot see a missing outcome. What each is
for, and the one rule that keeps a parallel build from losing work: `references/routing-notes.md`.

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

## The brief — a call and a folder, and that is the whole contract

> **The operator calls the factory and gives a folder. Nothing else is required of them.**
> Everything after that is either derived, or found inside that folder. They type a correction
> only when they want something other than what the factory would do on its own.

That is the acceptance test for this section. A colleague who types

    Redesign this module using the NOVIKONTAS Course Factory.
    C:\courses\Module_04

has given a complete brief. No skill name, no validator, no script, no flag, no folder layout,
no module split, no screen count — and none of those may be asked back.

**Look in the folder before asking anybody anything.** The programme, the sources, the existing
module, the expert's notes and the factory's own build record are usually all in there or one
level up, and a question whose answer was sitting in the folder is the fastest way to teach an
operator that this tool is hard work.

Only these three can genuinely be missing, and only these three may be asked — batched, never
one at a time, and never after the answer has been found on disk:

1. **Which accredited programme governs** — the approved document, by name or path. Without it
   there is no hours law and no ILOs, so this is the one blocking question.
2. **The knowledge base** — the docling-extracted sources for the subject.
3. **Has anyone edited this by hand?** — and only when `detect_expert_edits.py` says
   `nothing-to-go-on`. See L24; this question disappears permanently after the first run,
   because that run writes the build record.

Never ask: the module split, the screen count, the task codes, the pass marks, the file layout,
or which lane to load. Those are **derived**, and deriving them is this skill's job. Never
web-search during intake — not in the brief, programme or knowledge base means `UNKNOWN`.

**Corrections are the operator's only other input, and they arrive in their words.** "Too much
text on screen 4", "keep the old pump drawing", "this should be two screens" — act on them, and
do not turn a correction into an interview.

---

## The laws — the operative rule of each

These are not preferences; each is here because breaking it cost real rework. Numbered as in
`docs/FACTORY_LAWS.md`, the one numbering the whole factory uses.

> **The full text of every law — its reasons, its cases and its edge rules — is in
> `references/laws-in-full.md`.** Read the law in full before bending, questioning or changing
> one, and whenever an operator's request seems to collide with it.

**L1 · The approved programme is law, and minutes are its units.**
`hours/knowledge/hours-rules.json` is the authority. An academic hour is whatever the programme
says (GAS BASIC: 40 min) — never assume 60. Every module's built teaching time equals its
allocated minutes **exactly**; anything that will not fit becomes self-study in the handout.
Run `hours/scripts/check_hours.py` before believing any plan.

**L2 · Main ILOs are untouchable.** Main ILOs and the approved programme are copied
**verbatim** — never edited, renumbered or "improved". Sub-ILOs may be re-expressed; a
re-expressed Sub-ILO is `PROVISIONAL` until ratified and never renumbered in anything a trainee
sees. The programme governs; an IMO model course is guidance.

**L5 · Two tracks, and only one of them is yours.** Track A — the programme's theory/practice
allocation — is fixed: declare each block's bucket with `data-track` and run `check_balance.py`.
Track B — learner-active minutes — is designed: aim for 80 %, declared with `data-active`. Where
the practical share is small, the theory hours are delivered as active learning; a theory block
with no trainee activity in it is a defect. Never reach the target by renaming screens.

**L7 · Nothing is useless until you have grepped for what depends on it** — its id, class, label
and filename, across both terminals, the course tree and every generated script.

**L18 · Content is locked. The delivery implementation is not.**
`retrofit/knowledge/content-lock.json` is the authority. Locked, needing explicit authorisation:
technical meaning, programme requirements, ILOs and Sub-ILOs, official hours, assessment intent,
intended practical exercises, course terminology, source-supported facts, COURSE_LANGUAGE. Free:
screen count and order, HTML, layouts, density, visuals, animation, interaction, navigation,
CSS/JS, composition. An existing visual is evidence of a teaching decision — preserve the
decision, rebuild the implementation.

**L24 · Where the expert has already changed something, that change is content.**
`retrofit/knowledge/expert-edits.json` and `retrofit/scripts/detect_expert_edits.py`. Decided from
evidence — a marker the expert left, the factory's build record, a commit the factory did not
author — and if none exist, **ask**. A protected region is restyled, never rewritten; where it
breaks another law, name the law and propose the fix in the report — do not apply it.

**L21 · The production Android application is a publish target, not a workspace.** READ ONLY
without a person's own approval for that named course and version: *"Approved. Publish this
course to the NOVIKONTAS training app."* Review happens in the colleague's own folder
(`course-tablet-publisher` → `preview.py`); `publish.py --publish` refuses without `--approved-by`.

**L19 · COURSE_LANGUAGE is declared, and the operator's language is not it.** Detect it, state it
back in one line, lock it — in plan and retrofit alike. Course-facing material stays in it unless
translation is explicitly requested; the chat report and `factory-notes.md` follow the operator.
`retrofit/scripts/check_language.py` is the drift check.

**L25 · The person reading this does not work in IT.** `knowledge/plain-language.json` is the
authority; `scripts/check_plain_language.py` enforces it. Every problem message carries all five:

| | |
|---|---|
| **What is wrong** | one sentence, in the words of the course, not of the software |
| **Where it is** | the full path from the drive letter, plus the human landmark — which module, which slide, which heading |
| **How to see it** | the literal steps. Double-click what, opens in what, what appears |
| **What to do** | the fix in steps — and if the factory can do it, offer: *"tell me to fix it and I will"* |
| **How they know it worked** | what they will see afterwards. Never *"run the check again"* as the only proof |

This is not dumbing down: the maritime content stays exactly as technical as it is; what changes
is the language about computers and this tool. Offer to do the work before explaining how they
could.

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

## Build order

`knowledge/build-order.json` is the authority. Read it; it names the owning skill for each step
and what each step must not start without.

The shape, for orientation only (the file wins if this line ever disagrees with it): programme →
model-course syllabus → knowledge base → ILO map → module split → **gate** → per-module screen
inventory → **visual system** → **visual plan** → tasks → screens → handout → assessment → module
plans → terminals → verify.

Three orderings that are not negotiable, all three learned by getting them wrong:

- **Screen inventory before any screen exists.** `course-module-ux` owns that gate.
- **The visual system before any screen exists.** `course-module-ui` owns it, and for a new
  module it is a **required** step, not an optional polish pass — see below.
- **Task pages before the deck announces them.** A screen that announces `T3` when the tablet
  has no `T3` is the worst failure in the room, and it is only caught by the three-way
  cross-check in `tablet/`.

### The visual layer is routed, never improvised

When a new module reaches visual production, **route it to `course-module-ui`** — it owns the look,
and this skill restates none of it. Its `scripts/design_system.py install` copies the style files
(never read them); its `references/vocabulary.md` is what to read. GAS BASIC **Module_01 is the canonical visual reference** for the look, and
**not** a template: there is no canonical screen count, and low visible density is not low
learning depth. `build-order.json` step 8, `no_fixed_slide_count` and `density_is_not_depth` are
the contract; the reasoning is in `references/routing-notes.md`.

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
the line for the thing you changed. **Why each check exists, and what got through without it:
`references/verify-in-full.md`** — read it at sign-off.

1. `hours/scripts/check_hours.py` — minutes match the programme
2. `coverage/scripts/check_syllabus_coverage.py` — every **itemised outcome** of the model course is taught
3. `tablet/scripts/verify_course.py` — structure, counts, check→hand-off order
4. `tablet/scripts/verify_links.py` — every link resolves in the **merged** asset root
5. `tablet/scripts/audit_navigation.py` — every page is **reachable** and has a way back
6. `tablet/scripts/crosscheck_tasks.py` — deck ↔ run script ↔ tablet manifest agree
7. `course-module-ux`'s measurement lane for the screens themselves
8. `course-visuals/scripts/check_visuals.py` and `check_assets.py`; then, in the page,
   `GBVerifyFigures.run()` and `await GBVerifyFigures.motion()` (L20); then
   `course-visuals/review/GUIDE.md`. Nothing at `RIGHTS_REVIEW_REQUIRED` may ship.
9. `course-visuals/scripts/check_visual_first.py <module> --strict` (L23), then
   `course-visuals/scripts/write_visual_handoff.py <module>`
10. `course-module-ui/scripts/design_system.py check <module>`, then `audit_ui.py --strict` over a
    **new** module's stylesheets — never a delivered deck
11. `scripts/check_slide_text.py <course>` — what the pages SAY (L22)
12. `scripts/check_plain_language.py <course>` — your own report, last before sending it (L25)
13. `retrofit/scripts/detect_expert_edits.py <module> --record --version <v>` — **last of all**, after everything else passes (L24)
14. **In retrofit only** — `retrofit/scripts/check_language.py <course> --declare <LANG>`, and
    `retrofit/scripts/classify_module.py` **again**

Then write `templates/factory-notes.md` into the course folder: what was produced, every marker
with its source, the achieved ratio, what was moved to the handout and why, and a final section
of **feedback on this skill**. That last section is the only channel through which real use
reaches the skill — it is written by this skill during the run, never left for a human.
