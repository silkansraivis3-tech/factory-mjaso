# course-factory — MANIFEST

**v1 (2026-09-07) · Maintained by Raivis · part of the `course-factory` plugin, shared with colleagues through the marketplace**

Maintainer file. **Not read at runtime.** It exists so a session six months from now can pick
this up cold, including one with no memory of why any of it is the way it is.

---

## 2.75.1 · Editor-mode fixes back into the script (2026-10-29)

- **Why.** The training app's editor fixes a slide with Claude and publishes it as a draft release, but the course folder
  is the source: a fix that never reaches the script is undone by the next build.
- **What.** `scripts/editor_fixes.py read | propose` turns the editor's export into PENDING script changes (title, text,
  notes), applied only on the operator's yes; what it cannot take is named. fix/GUIDE.md section 3c.

## 1 · Design principles

- **This skill is a router and a law, not a builder.** It owns order, the hours law, ILO
  immutability, the ratio rule and the terminal contract. It writes no screens and no tasks —
  `course-module-ux` and `course-task-ux` do that, and they existed first.
- **Every rule in here is here because breaking it cost real rework on GAS BASIC.** Nothing is
  aspirational. Where a rule has a story, the story is in the skill, because a rule nobody can
  trace is a rule nobody follows. Since 2.11.0 the stories live in `references/`, word for word,
  one pointer away from the rule — see §4c.
- **The hours law is the reason this skill exists.** `COURSE_START.json` — the contract that
  orders the whole Novikontas course factory — has **no hours field at all**, and GAS BASIC was
  built 535 minutes (33 %) over its accredited allocation before anyone counted. This skill adds
  the field and the counting.
- **Determinism over attention.** Four checkable things are checked by scripts with exit codes,
  not by remembering. Each script was run against GAS BASIC before shipping, and **three of the
  four found real bugs on their first run** — which is the point.
- **Narrow beats loud.** Every check here was over-reporting when first written. A check that
  cries wolf trains its user to ignore it, so each was narrowed to what it can actually prove,
  and what it cannot prove is printed as ADVISORY rather than dressed up as a failure.

## 2 · Architecture

```
course-factory/
├── SKILL.md                              router: mode, brief, the laws (operative rule each), gate, build order, verify list
├── MANIFEST.md                           this file
├── references/                           READ WHEN NAMED — the full text moved out of SKILL.md in 2.11.0
│   ├── laws-in-full.md                   every law with its reasons and cases, word for word
│   ├── owner-decisions.md                every Phase 5 row (L27-L61) in full, one heading per law (2.50.5)
│   ├── verify-in-full.md                 why each verify check exists
│   └── routing-notes.md                  what orchestration/ and coverage/ are for; the visual-layer routing
├── knowledge/
│   ├── build-order.json                  the 15 ordered steps + who owns each (authority)
│   └── delivery-contract.json            paths, flavours, course pack, git, offline (authority)
├── knowledge/intake.json                 Stage 1: look first, the pop-up questions, the intake record (2.13.0)
├── knowledge/course-type.json            NEW_ENTRANT / EXPERIENCED - what each changes (L28, 2.13.0)
├── kb/                                   READ IN: intake, and whenever sources are needed (2.13.0)
│   ├── GUIDE.md
│   └── scripts/kb_tool.py, test_kb.py    both knowledge-base kinds; copies, editions, search - never writes into the KB
├── templates/
│   ├── COURSE_BRIEF.md                   what the operator types
│   ├── COURSE_STATE.md                   where the course stands - read first by every session (L32, 2.14.0)
│   ├── FEEDBACK_LOG.md                   every operator correction, in their words (L32, 2.14.0)
│   ├── COURSE_PATTERN.md                 what a finished course teaches the next one - approved by the operator (L32, 2.14.0)
│   └── factory-notes.md                  companion file, written by the skill during the run
├── scripts/course_memory.py, test_course_memory.py   start / check the state; draft and approve a pattern; list approved patterns
├── scripts/make_architecture_page.py, test_architecture_page.py   the Stage 2 STOP as one page (2.15.0); one module per topic (2.17.0)
├── knowledge/theory-rules.json           how much theory before any task, and the two tablets (L35, L36, 2.17.0)
├── scripts/workspace.py                 the work folder: course\ beside the operator's material (L40, 2.19.0)
├── scripts/check_course_package.py, test_course_package.py   the course folder to the classroom's rules + its own importer (L45, 2.21.0)
├── scripts/check_module_folder.py       kept as a short way in: runs check_course_package.py (2.21.0)
├── knowledge/classroom-system.json      the classroom system's own course-folder rules (L45, 2.21.0)
├── scripts/picture_briefs.py, test_picture_briefs.py   generated pictures: places, the person's description, cost (L47, 2.24.0)
├── scripts/exercises.py                 a module's practical exercise forms; its slide proposed from the TRAINEE form (2.63.2)
├── bloom/GUIDE.md                       READ IN: judging or lifting a Bloom level - Stage 2, Stage 3, retrofit (L48, 2.25.0)
├── knowledge/bloom.json                 the six levels, verbs (en / lv / ru stems), each task type's usual and highest level, floors
├── scripts/bloom_map.py, test_bloom_map.py   the Bloom map: ILO levels, task levels, gaps, how to lift - drawn on both review pages
├── scripts/test_active_split.py         20 / 80 in class: plain theory against active minutes on both pages (L49, 2.26.0; theory-rules.json split)
├── active/GUIDE.md                      READ IN: Stage 2 - proposing theory as activity per sub-topic, recording the operator's decisions (L49, 2.27.0)
├── knowledge/active-learning.json       the patterns proposals are written from (fits, what the trainees do, minutes), the rules, the statuses
├── scripts/active_plan.py, test_active_plan.py   list what waits; decide - kept / struck, logged with the operator's words, page re-rendered
├── scripts/test_new_task_types.py      the five tasks for the higher Bloom levels, end to end (L49 step 4, 2.28.0)
├── fix/GUIDE.md                         READ IN: fix mode - a correction to built modules: find, one list, one yes, change, one check (L50, 2.29.0)
├── knowledge/fix-rules.json             the sweeps and their thresholds, the check for each kind of change, what never runs in a fix, standards, shared parts
├── scripts/fix.py, test_fix.py          sweep / propose / apply / approve / check / standard / sync-shared - every module at once, one yes for all of it
├── scripts/measure_slides.py            every slide of many modules at 1280 x 800 in a hidden Chrome or Edge, animations finished, ~4 s a module
├── knowledge/design-rules.json          the DESIGN rules a person may choose against after one warning, each with the risk to say (L26, 2.30.0)
├── scripts/design_choices.py, test_design_choices.py   rules / list / add - a choice recorded in STANDARDS.md, obeyed by every check
│                                          knowledge/media-and-tasks.json three_d: 3D on at most half the slides, where it makes sense, full quality, smooth (L46, 2.22.0)
├── scripts/old_course.py, test_workspace.py   the old course read whole, its pictures copied out (L41, 2.19.0)
├── knowledge/media-and-tasks.json        the kinds of picture and the ways of answering, who makes each, the variety floors (L37, L38, 2.18.0)
├── knowledge/page-labels.json            the review pages' own words in the operator's language (en / lv / ru)
├── script/GUIDE.md                       READ IN: Stage 3 - the content script (2.16.0)
├── scripts/content_script.py, check_script_match.py, test_content_script.py   the script, the Word copy, corrections on confirmation, the word-for-word match
├── compile/GUIDE.md                      READ IN: building the deck from the approved script (2.25.0)
├── compile/scripts/compile_module.py, test_compile_module.py   the deck built, never typed; build sheet; hand edits never overwritten
├── compile/scripts/compile_course.py, test_compile_course.py   COURSE.html, course_map.js, every module's start pages (2.37.0)
├── compile/scripts/task_pages.py, test_task_engine.py   every trainee task page, all 19 ways of answering; the engine driven in Chrome (2.38.0)
├── scripts/ilo_map.py                    the ILO map file, built from programme.json + architecture.json (2.42.0)
├── scripts/ilo_coverage.py, test_ilo_coverage.py   _course_shell/ilo_coverage.json for the admin panel, written by compile_course.py (2.83.0)
├── scripts/course_gate.py, gate_fixture.py   no module before the approved ILO map and the KB decision; the tests' opener (2.42.0)
├── hours/                                READ IN: plan mode, and audit
│   ├── GUIDE.md
│   ├── knowledge/hours-rules.json        every number and rule (authority)
│   └── scripts/check_hours.py            the budget gate
├── coverage/                             READ IN: audit mode
│   ├── GUIDE.md
│   └── scripts/check_syllabus_coverage.py
│                                         every ITEMISED outcome of the model course
└── tablet/                               READ IN: ship mode, and audit
    ├── GUIDE.md
    └── scripts/
        ├── verify_course.py              structure, order, chain, count claims, stray files
        ├── verify_links.py               links resolved in the MERGED asset root
        ├── audit_navigation.py           reachability, a way back, depth, outcome codes
        └── crosscheck_tasks.py           deck <-> run script <-> tablet manifest
```

Lane assets live under the lane. Root holds only what the router needs.

**Why there are six checks and not four.** `check_syllabus_coverage.py` and
`audit_navigation.py` were added on 2026-09-07, after the other four all passed on a course that
was **missing an accredited outcome** (IMO 1.04 item 9.2.7, decontamination showers and eyewash —
in no screen, task, document, handout or assessment) and **shipping a 28-page section nothing
linked to** (every safety brief, rotation plan and practical write-up in the instructor terminal).
Each answers a question none of the others asks:

| passes when | but says nothing about |
|---|---|
| `check_hours` — the minutes add up | whether the content is there |
| `verify_links` — every link resolves | whether anything links to the page |
| `verify_course` — the deck is sound | outcomes inside a topic |
| `crosscheck_tasks` — the wiring agrees | either of the above |

Every check in this bundle was added after something got through the ones before it.

## 3 · Provenance

| item | source | disposition |
|---|---|---|
| the hours law, the overflow-to-handout ruling | owner decision, 2026-09-07 | **New** |
| the accredited table for GAS BASIC | `1. Program Basic Training Gas - Rev. 01` §6, transcribed and reconciled against its own Total row | **New** (as a worked example in `hours-rules.json`) |
| `check_hours.py` | **New** — written for this skill; nothing counted minutes before it | **New** |
| `verify_links.py` | generalised from `verify_merged.py`, written this session for GAS BASIC | **Carried** (parameterised, hard-coded paths removed) |
| `crosscheck_tasks.py` | generalised from the session's three-way check | **Carried** (parameterised) |
| `verify_course.py` | generalised from `coverage/verify_all.py` | **Carried** (parameterised; the `.slide-body` invariant corrected from "exactly one" to "at most one") |
| screen craft, one-page architecture, deck measurement, run-script generation | `course-module-ux` | **NOT copied** — point at it. It is the specialist and it is already course-agnostic. |
| trainee task screens | `course-task-ux` | **NOT copied** — point at it |
| course intake (type, accreditation, equipment, regulations) | `novikontas-course-intake` | **NOT copied** — it owns intake and runs before design |
| the course-plan document, competence matrix | `novikontas-course-plan` | **NOT copied** — it designs the plan; this skill enforces the numbers |
| `COURSE_START.json` contract, marker definitions, traceability tiers, gap report | `novikontas-course-start` | **NOT copied** — the marker set is used identically and the contract is only ADDED to, never altered |
| ILO wording, verbs, constructive alignment, assessment design | `novikontas-pedagogy-toolkit` | **NOT copied** — this skill owns only ILO *immutability*, not ILO *wording* |
| exercise forms, handouts, written tests, pptx decks | the `novikontas-*` material skills | **NOT copied** |
| visual identity | `novikontas-brandbook` | **NOT copied** |

## 4 · Conflicts found and resolved

| conflict | resolution |
|---|---|
| Owner wants 80/20 practical; the accredited programme allocates 19 % and the split is fixed by its own table | Two tracks. **Track A** is the programme's allocation, not editable, and the build must deliver it bucket for bucket (`data-track`, `check_balance.py`). **Track B** is delivery modality (`data-active`) and is where the 80 % target lives: theory hours are **delivered as active learning**, and a theory block with no trainee activity is a defect. Owner's own fallback, made mandatory and now measured. |
| `novikontas-course-plan` owns "theory/practice ratio"; this skill also rules on ratio | Boundary: that skill **designs** the plan and states the ratio; this skill **enforces** the accredited arithmetic and owns the active-learning fallback. Named in the router's boundary table. |
| IMO model course vs approved programme | The programme governs. The model course is guidance, cited as support, never as authority. |
| `COURSE_START.json` has no hours field, but is owned elsewhere | Additive `hours` block only. The existing schema is never altered. Shape in `hours-rules.json`. |
| Memory said "exactly one `.slide-body` per section" | Wrong as a universal: photo, launch and check screens use other body classes. Corrected to **at most one**; two is the destructive bug. |

## 4b · The retrofit lane (added 2026-09-11)

`retrofit/` exists because of one failure mode that no check could see: a colleague asked for an
existing module to be brought up to GAS BASIC quality, and got back a technically correct retrofit
that still felt weaker than GAS BASIC. Nothing was broken. Every individual decision to keep an
existing layout was defensible. The sum was a module that passed everything and was not the product.

**Conservatism looks like diligence.** That is why the law had to be written down rather than left
to judgement:

> PRESERVE THE COURSE CONTENT. DO NOT PRESERVE THE EXISTING DELIVERY IMPLEMENTATION BY DEFAULT.

| file | is |
|---|---|
| `retrofit/GUIDE.md` | the lane — nine steps, from COURSE_LANGUAGE to the acceptance question |
| `retrofit/knowledge/routing.json` | which mode a free-form request selects, and retrofit vs restyle |
| `retrofit/knowledge/content-lock.json` | what is locked, what is free, and why an existing visual is evidence rather than implementation |
| `retrofit/knowledge/classify.json` | the A/B/C signals, and the `not_signals` list that keeps "the HTML works" out of the decision |
| `retrofit/scripts/classify_module.py` | measures the six signals and returns the level |
| `retrofit/scripts/check_language.py` | COURSE_LANGUAGE drift over course-facing files |
| `retrofit/scripts/check_terms.py` | 2.63.2 - one thing, one name across the whole course: mixed use of a synonym group (LEL / LFL ...) with where each form is used; a report, run in `build_course.js` assembly. List: `knowledge/terms-default.json` + the course's `working_claude/terms.json` |
| `retrofit/scripts/test_check_terms.py` | the report on a fixture course (approved vs draft scripts, a page-only module, an own list) |
| `retrofit/scripts/check_numbers.py` | 2.63.2 - one quantity, one value across the whole course: a number with its unit and the key word before it (`compile_module.facts_in`, imported) stated with close but different values in two places (20 ppm / 25 ppm, 20.9 % / 21 %) with where; a report, run in `build_course.js` assembly next to `check_terms.py` |
| `retrofit/scripts/test_check_numbers.py` | the report on a fixture course (a slide against a question, close vs far values, the final test read once, a draft script, a page-only module) |
| `retrofit/scripts/test_routing.py` | 42 deterministic assertions over all three knowledge files |

**Two things the classifier got wrong before it was right**, both worth keeping in mind if it is
ever extended:

1. It scored `canonical_shell` and `token_adherence` on **filenames** — and classified GAS BASIC
   Module_01, the design authority, as "needs moderate redesign", because it loads
   `presentation.css` rather than `gb_shell.css`. Those files were extracted *from* it. Both
   signals now measure the system: the shell's structural landmarks wherever they live, and a
   declared token set wherever it is declared.
2. It scored composition against **our vocabulary**, and marked the golden down for using
   `exp-stage`, `sil-row` and `handover` — the names ours was derived from. Any modifier class on
   `.slide-body` now counts; what is measured is whether the author chose a composition per screen,
   not whether they chose ours.

The test suite is mutation-tested: removing the `only` scope limiter and removing `the HTML parses`
from `not_signals` each produce exactly one failure.

## 4c · Lighter loading (2.11.0, 2026-09-30, Phase 5 step 11)

The owner approved moving — never deleting — the long reasoning out of the file every session
reads. `SKILL.md` went from **30,444 to 19,068 bytes (≈7,600 → ≈4,800 tokens)**. What moved, word
for word: the full text of every law (`references/laws-in-full.md`), the reason each verify check
exists (`references/verify-in-full.md`), and the orchestration / coverage / visual-layer notes
(`references/routing-notes.md`). Each law keeps its operative rule in `SKILL.md` and a pointer.
Proof it was a move: a line-by-line comparison of the old file against the new file plus the
three references found every line except the version stamp. Future detail goes into a lane or
`references/`, never back into `SKILL.md` — that is the point of the exercise.

## 4d · The owner's decision record (2.12.0, 2026-09-30, Phase 5 step 1)

Eight laws, **L26–L33**, from the owner's Phase 5 decision record — full text appended to
`references/laws-in-full.md`, one-line operative form in `SKILL.md`'s *Owner decisions in force*
block, which says that where any older rule disagrees, the decision wins, even before the step that
builds it out has landed. That block is how a decision reaches a session before its step exists:
`SKILL.md` is read at the start of every course job.

**L26 is the one built out now**, because the owner's reviewer found the factory refusing or
ignoring colleague requests as "not in the style":

- a new **edit** mode in `retrofit/knowledge/routing.json` (`edit_triggers`): a change word plus a
  course object, with no whole-module intent, is done as asked. Before, "add two slides on cargo
  pumps" matched no mode and fell to *ambiguous* — a clear instruction answered with a question.
  `test_routing.py` implements and asserts it, in English, Latvian and Russian;
- `content-lock.json`: the operator's request in chat **is** the explicit authorisation;
- `expert-edits.json`: a protected region is protected from the factory, never from the operator;
- one line each where a rule read like grounds to refuse: `course-module-ux` laws 3, 4 and 7,
  `course-task-ux`'s "not negotiable", `course-visuals`' "never add a visual to fill space".

The five hard limits are the only exceptions: brand, programme + Main ILOs, hours, no source no
claim (an operator's stated fact is a source), offline tablet. *(2.30.0: the brand moved to the design side - the
person's after one warning, see 4z; the material keeps the other four.)*

## 4e · Intake and the knowledge base (2.13.0, 2026-09-30, Phase 5 step 2)

The old brief allowed **three questions, ever** — programme, knowledge base, hand edits — and assumed
every knowledge base was a docling extraction. The owner's process needs more at intake (old course,
course type, model course, which edition is current) and the owner's own tool, the Course Source
Processor, was unknown to the factory.

- `knowledge/intake.json` — look in the folder first, then **one batch of pop-up questions with
  options** for what is still missing, then `_factory/intake.json`. Equipment the IMO model course
  lists is assumed available (L28) and never asked.
- `kb/scripts/kb_tool.py` — reads both kinds by their files. `sources` sorts the knowledge base
  before anything is cited: exact copies (cited once), the same document as .doc/.docx (newer format
  cited), and **editions of one publication** — by name with the year and edition removed, by
  acronym (LGHP, ISGOTT), by typo (SIGGTO/SIGTTO) — each written as a ready "which edition is
  current?" question. Different numbers mean different documents (exercise 14.2.4 is not 14.2.5, model
  course 1.04 is not 1.35); a short differing word is not a typo (LNG/LPG). `decide` records the answer;
  `search` then leaves the old edition out. Packs go to `course/working_claude/retrieval/`, **never into the
  knowledge base**; a `--course` that is not an existing course or master folder, or sits in the factory or a
  knowledge base, is refused (2.48.1).
- Run read-only on the two real knowledge bases on this machine: GAS BASIC (docling, 48 sources) —
  3 exact copies (the SIGTTO book three times), 1 .doc/.docx pair, and 2 edition questions (MARPOL
  2022 against an older MARPOL; ICS Tanker Safety Guide 3rd ed. against an undated one). The electrical
  course (Course Source Processor, 565 sources) — 53 exact copies and 7 edition questions. Search took
  1–3 seconds; both knowledge bases were fingerprinted before and after and did not change.
- The first matching rules grouped LNG with LPG, two numbered exercises and the two IMO model
  courses; the real run caught all three before they reached a test, and `test_kb.py` now pins them.
- **2.13.1 — `find`.** The operator gives a course folder, not a knowledge-base path, and the intake
  rule said "the folder and its sub-folders" while the script checked one folder. `find` walks the
  course folder, its sub-folders and one level up, recognises each knowledge base by its files, never
  walks inside one, and writes nothing; several found become one ready question. Tested read-only on
  the owner's pilot folder (`Desktop\mjaso-factory-test`): one Course Source Processor knowledge base,
  47 sources, found from the folder and from its `old_course` sub-folder; the folder was fingerprinted
  before and after and did not change.

## 4f · The course remembers (2.14.0, 2026-09-30, Phase 5 step 3)

L32 built out. `COURSE_STATE.md` is started at intake and updated at every STOP; `course_memory.py
check` says whether a new session could resume from it (every section, a named stage, a next step, a
date, a feedback log beside it). `FEEDBACK_LOG.md` takes every operator correction in their words, and
marks the facts they stated so step 5's content-script review can list them (L29).

The pattern file follows the owner's three conditions: it is **shown to the operator in plain language
and saved only on their approval** (`draft-pattern`, then `approve-pattern --by <name>`; they may change
or remove any point); it **names the course, the course type, the subject and who made it**, and
approval is refused until it does; and patterns are **guidance, never rules, never above the current
operator's request** — the listing says so every time, and never shows a draft or an unapproved file.
Approved patterns live in `plugin/resources/course-patterns/` (the owner copies them there and
commits); the name `resources/patterns/` was already taken by the visual engines.

The publisher now sorts `COURSE_STATE.md`, `FEEDBACK_LOG.md`, `COURSE_PATTERN_*.md` and
`factory-notes.md` as INTERNAL, like `REVIEW.html` and `_factory/`. `factory-notes.md` had not been
covered before; no file of any of these names exists in the Android project, so GAS BASIC's
publishing is unchanged. The first attempt at that publisher change failed silently on shell escaping;
the new test caught it before anything was reported, and every edit since is re-read after saving.

## 4g · The architecture page (2.15.0, 2026-09-30, Phase 5 step 4)

The Stage 2 STOP used to be a table in the chat. It is now `ARCHITECTURE_REVIEW.html`, written by
`scripts/make_architecture_page.py` from `programme.json` and `plan.json` (the same files
`check_hours.py` reads, with optional verbatim topic `title` and programme `ref` per topic, and
optional `main_ilos`) plus `architecture.json` (ILOs, Sub-ILO changes, active learning, practicals,
test plan). One self-contained file: the style is inlined from `gb_tokens.css` and `gb_page.css`,
nothing is fetched, and it prints to PDF.

The owner's three conditions: **every Sub-ILO beside the programme's own wording, marked kept /
re-expressed / added**, with the reason, because "next" ratifies them; **programme text and Main ILOs
verbatim in COURSE_LANGUAGE** (marked with its `lang`), headings and explanations in the operator's
language (`knowledge/page-labels.json`, en / lv / ru, every label present in all three); **each
module's hours with the programme topics and rows they come from**, checked against the plan.
`--check` catches hours that disagree, unclaimed topics, a Sub-ILO change with no programme wording,
an added one with no reason, a Main ILO that is not word for word, a graded module check and an
ungraded final (L1, L2, L27) — and the page puts them at the top, before what "next" approves.

The page and its three input files are INTERNAL to the publisher. The page was checked in headless
Chrome (screenshot) and prints to a 4-page PDF for the example; the printed pages themselves were not
looked at, because no PDF renderer is installed on this machine. Stage 2 does not show a screen count
any more — screens come out of the Stage 3 script.

## 4h · The content script (2.16.0, 2026-09-30, Phase 5 step 5)

L29 built out. `_factory/script/M01.json` holds every screen in trainee order — slides with their exact
words, planned picture, notes and minutes; each self-check and module-check question its own screen —
and `content_script.py render` turns it into a review page and **a Word file**, the operator's copy
(owner: colleagues do not use Markdown). Every editable text is a Word content control tagged
`<screen>.<field>` and locked against deletion (`sdtLocked`), so typing works and deleting a box does not.
The file is written and read with the standard library only.

The owner's conditions: typed text and Word comments are both read; tracked changes are read as if
accepted and reported as tracked, with the author; a deleted box and text typed outside the boxes are
reported, never guessed. **Nothing is applied from reading**: `read` and `propose` write a pending list
and print what was understood, only in the changed words ("'rely on' becomes 'are supported by'");
`apply --confirmed` applies it after the operator says yes, logs every change in `FEEDBACK_LOG.md`,
keeps the old Word file and writes a fresh one; comments are instructions and are never applied as
edits. Approval refuses while anything waits; any change after approval makes the module a draft
again. `check_script_match.py` proves the built slides and tasks carry exactly the approved words, via
`data-script` / `data-script-field`, and fails any module built from an unapproved script.

**Proved with real Word** (Microsoft Word on this machine, driven through its automation interface,
2026-09-30): Word opened the generated file (36 boxes), a box's text was retyped, a comment added on a
title, an answer reworded with Track Changes on, and deleting a box was **refused by the lock**; after
Word saved, `read` found all three, placed the comment on the right field and named the tracked change's
author. **PDF comments**: a review page printed to PDF by Chrome, with a reader-style comment added,
was read back with its page and the screens on that page — approximate by nature, and it needs the
`pypdf` package. `test_content_script.py` simulates the Word edits in the file's XML so it runs on any
computer.

**2.16.1 — the slide-text check runs on the script.** At 2.16.0 the L22 check only read built pages, so an
internal abbreviation or a model course cited as a source was caught after the HTML — the thing Stage 3
exists to prevent. `check_slide_text.py` was split into `scan_file` (reads a page) and `scan_text` (the
four rules on text), with no change in behaviour — its 16 tests pass unchanged. `content_script.py`
feeds every screen's fields to `scan_text`: trainee-facing text as a presentation page, the instructor
notes and the planned-picture note as instructor-only. The findings head the review page and the Word
file; `approve` refuses while a must-fix one stands, unless the operator approves `--despite-findings`
(L26), which is recorded. The new test ran one time in five into a real bug: two corrections applied in
the same second gave the archive the same file name, the rename failed and the pending list stayed
behind, blocking approval. Archive names are now unique (`archive_name`), a test pins it, and six
consecutive runs passed clean.

## 4i · The owner's review of the example pages (2.17.0, 2026-09-30)

The owner read the two example pages and rejected three things; each became a law, and both tools were
rebuilt around it.

- **"Why only 2 modules?" - L34.** The modules are the programme's topics, one each, with the
  programme's hours; the final-assessment topic is the last module and the assessment only. The
  architecture page now builds the modules straight from `programme.json` (`plan.json` is optional,
  for built minutes only), shows an overview of all of them totalled against the programme's own total
  row, and gives every module a *where the minutes go* table. It catches merged topics, teaching inside
  the assessment, an assessment that is not last, a module the programme does not have, a teaching module
  with no module check, more self-checks than the theory time allows, and a total that disagrees with the
  programme. The academic hour is 40 min when the programme is silent, and the page says so. Programme
  text is marked with the programme's own language, module titles with the course language.
- **"Why did you put tests inside slides?" - L35.** Two tablets: slides on the instructor's, mirrored to
  the classroom screen; tasks only on the trainee's. And, from the owner mid-step: a task opens only when
  the instructor presses OPEN TASK, on every trainee tablet at once; no task list, no browsing, no "all
  tasks" or "back". The content script gained the `task-slide` kind (the slide that only announces the
  task, and carries OPEN TASK on the panel) and task sets (`"set"`); the review page and the Word file
  are now in two parts, instructor tablet and trainee tablet, and every set ends on the trainee's own
  score - "self-check does not mean there is no score for the trainee; it's for himself". Questions are
  named "Self-check 1, question 2", slides "Slide 7", in every message. `course-task-ux` §3's task-list
  rulings are marked as the old app's. The tablet app does not work this way yet - its change list is
  step 6 (L21).
- **"Slide text is too small" and "enough theory before the self-check" - L36.** `knowledge/theory-rules.json`
  holds the floors and `theory_findings` checks them on the script: 50-150 words on a slide, 30 in the
  notes, 40 words per theory minute across the module, 10 min and 400 words of new theory before a
  self-check, 3-6 questions in a self-check and 5 or more in a module check, no task written onto its
  slide, and every question's correct answer already taught - its key words (numbers exactly, words by
  their first five letters, leaving out words the wrong answers share) found in the slides before it.
  The page shows, for every question, the slide that teaches its answer. Findings block approval unless
  the operator approves despite them (L26).

Found on the way: the test module the factory wrote for itself failed its own new floors (34 words a
minute, 357 words before the self-check) and was rewritten to them; and the first answer check let an
untaught answer pass because the wrong options shared its words - fixed by comparing only the words that
make the right answer right.

The example pages were remade: the architecture from the real GAS Basic programme (Rev. 01.07.2026, read
from the pilot knowledge base, read-only) - 23 modules; the content script as a full 80-minute Module 1
written to the floors, and a second copy with six planted problems.

## 4j · Pictures, animation, 3D, and tasks that are not A, B, C, D (2.18.0, 2026-09-30)

The owner, on the rebuilt examples: *"leave place for animations, images, 3D illustrations ... and mention what
kind would be used"*, and *"make these tests more variable ... as much variable as possible ... if you cannot
perform, explain why and advise how"*. And, mid-step: *"courses are only in English"*.

- **L37.** `knowledge/media-and-tasks.json` lists 18 kinds of picture (each tied to a `course-visuals`
  representation) and five makers - the factory itself, the image/video generator (nano-banana: Gemini images,
  Veo video; the key was checked working on 2026-09-30), the sources, Novikontas, outside help - with how each
  is made. The content script gained `visual_kind` (an editable Word box in the operator's words, read back to
  its id) and `layout`; the review page draws each slide with its picture area beside the text, and lists what
  Novikontas or outside help must provide. The architecture page gained a per-module picture plan, a Pictures
  column in the overview, and a course-wide *who makes them* list.
- **L38.** Fourteen ways of answering, none typing, each with a one-box text form the operator can edit in Word
  (`answer`, one line per item, `*` for right). `read_answer` checks each form and gives the right and wrong
  words to the was-it-taught check (L36), so it now works for ordering, matching, sorting, scenarios and the
  rest. `media_findings` checks the floors. The review page draws each task as the tablet will: a sorting board,
  a slider, a numbered order, a pairs table, gap choices, scenario steps. `check_script_match` compares an
  answer's pieces as a set (the tablet shuffles them) and checks what is marked right.
- **What the factory cannot make itself, and how it gets made** (said on the pages and here): the exact look of
  a named piece of equipment in 3D - scan the real one at Novikontas with a phone photogrammetry app (Polycam,
  KIRI Engine, RealityScan) to a .glb, or use a manufacturer's CAD or a licensed model, or a 3D artist; AI
  image-to-3D services (Meshy, Tripo, Rodin) through their own API key for context objects only. Real procedure
  video - film it at Novikontas (no video editor is installed here; short clips can be used as filmed).
  Everything else - SVG, animation, interactive diagrams, three.js 3D from geometry, every task mechanic - the
  factory builds, bundled for the offline tablet. The trainee-tablet side of the new tasks and OPEN TASK is the
  app change list of step 6.
- **English only.** Every Novikontas course is in English: COURSE_LANGUAGE is never asked (`intake.json`), and
  L19 carries the owner's note. Review pages still follow the operator's language.

The examples were remade: Module 1 now has 13 slides with 8 kinds of picture (3 of them 3D models, 2 step
animations, an interactive drawing) and 14 questions answered 10 different ways; the architecture plans pictures
and ways of answering for all 22 modules and lists what Novikontas must photograph, film or scan.

## 4k · Short instructor notes, pictures without a quota, and who tests where (2.18.1, 2026-09-30)

- **Notes.** *"Compact and smaller, and keep them in a .md file - it will be in the instructor's panel, not in the
  slides."* `theory-rules.json` notes: 10-50 words (a ceiling is new); `content_script.py` writes
  `instructor_notes/M01_INSTRUCTOR_NOTES.md` on every render - one section per slide, the OPEN TASK prompt at every
  task, in the course language. The review page shows them as points under *Instructor panel only*. The publisher's
  roles gate now names `*_INSTRUCTOR_NOTES.md` as instructor-only. With the notes short, the density floor fell from 40
  to 25 words a theory minute and the block before a self-check from 400 to 250 words - the slides are unchanged.
- **Pictures.** The owner, asked how to treat the pasted proposal to turn the variety rules into warnings: no quota for
  pictures - as many as show the theory, animation and realistic 3D always welcome. So a slide with no picture, a long
  module with nothing moving and few kinds of picture are notes on the review page, and on the architecture page they
  move to a *Suggestions - not required* box that does not fail `--check`. The task rules were left as they are - the
  owner did not ask to change them. The final assessment was already outside them.
- **L39.** The real-tablet test is the owner's, at the end; colleagues get only the HTML to check in their own browser;
  the build makes every file ready for the tablet system. Recorded in the laws, `tablet/GUIDE.md` and the pilot's state.

## 4l · The work folder, the old course as the foundation, every picture usable (2.19.0, 2026-10-01)

- **L40.** *"After I choose the folder ... do all the work in another folder inside the master folder."*
  `scripts/workspace.py` tells a master folder (it holds source_files, a knowledge base or an old course) from the
  factory's own work folder and returns `<master>\course\`, made on first use. Every tool that writes - the content
  script, the architecture page, the course memory, the knowledge-base decisions - calls it, and the match check
  reads through it, so either folder may be named. A folder with no material in it is used as it is.
- **L41.** *"Check all of the old course, take it as fundamentals, and from there think how it can be optimised,
  modernised and digitalised."* `scripts/old_course.py inventory` reads every file of the old course - each deck
  slide by slide (title, words, pictures, speaker notes), each document's headings and words, PDFs' pages, the films -
  flags an old `.doc` as not read and leaves lock files out; `images` copies every picture out of the decks, each named
  by its slide, a repeated logo kept once. On the pilot's old course: 79 files in 17 sections, 438 slides, 653 distinct
  pictures (1,624 placed), 23 training films, read in about a second, the old course unchanged (fingerprinted). The
  architecture page gained a per-module *from the old course - kept, modernised, added* table, required once
  `course.old_course` is set; a slide may carry `from_old`.
- **L33 revised.** *"All images he can find in the knowledge base and the old course are usable, and if needed, he
  MUST go to the internet and download all images needed."* `OWNER_CLEARED` is a new rights state for both;
  `RIGHTS_REVIEW_REQUIRED` on an internet download now goes on the owner's licence list instead of blocking the build;
  the sourcer returns its download list first, shown once per module, and downloads on the operator's yes. Equipment a
  trainee must recognise is still never an AI image.
- **Found on the way:** the pilot had already been started in another session (2026-10-01, 09:36) and was already
  working in `course\` - the layout this release makes the rule. Nothing in the pilot folder was touched by this release.

## 4m · Every reply is human (2.19.1, 2026-10-01)

*"Every response needs to be humanized and understandable - by points: what's done, what's next, what to check now -
for a person who knows zero about IT."* `SKILL.md` now opens with the rule - three parts, **Done · Check now ·
Next**, short points, everyday computer words, maritime terms unchanged - with the headings in English, Latvian and
Russian; `plain-language.json` → `every_reply` holds it with a list of words to replace; the five other skills carry
one line pointing to it, so a session that starts in any of them follows it too.

## 4n · Tasks for someone who has never held a tablet (2.19.2, 2026-10-01)

*"For tablet tasks I need tablet-friendly UI/UX, user-friendly as well, but max modern, max technology and max
understandable - so people even with zero tablet experience do the tasks, and they are excited."* `course-task-ux` §0 is new and comes first: the zero-experience test, the *try the tablet* screen,
tap and drag only, the gesture hint, bigger controls and text (the §11 floor raised for answer controls on the trainee
tablet), alive feedback, real equipment, forgiving, offline, and how it is proved. The numbers are in
`media-and-tasks.json` → `trainee_tablet_experience`; building it is step 6.

## 4o · Every module in its own folder (2.19.3, 2026-10-01)

*"Put all modules in one folder, each module has its own folder, and all assets and scripts needed for that module to
start are inside each module folder; there is a START HERE HTML where it opens the presentation straight away, but the
extended start has fast access with buttons for all tasks, the module plan, the presentation and so on."*

The layout is in `delivery-contract.json` → `module_folders`, `course-module-ux` and `tablet/GUIDE.md`.
`check_module_folder.py` finds `M01_...` folders from the master, course or modules folder and checks each: both start
pages, START HERE going to the presentation (a redirect or a link), a button on the extended start for the
presentation, every task page and the plan and notes, every referenced file inside the module and present (src, href,
inline and `<style>` url()), nothing from the internet. The publisher now also names `START_HERE_EXTENDED.html`
instructor-only. `check_script_match.py` looks for `modules\M01_*` first and the older `modules\m1` after.

## 4p · Three places in the work folder (2.20.0, 2026-10-02)

*"All files the instructor can see and check go into a to_review folder - all scripts, the architecture,
everything - and all other stuff that is useful only for Claude himself goes into his own folder, working_claude, so
each module has a normal folder structure and every file that needs to be checked by the instructor is in one place.
That does not mean you remove or stop adding checkpoint and context .md files - just put them in the folder for files
only Claude uses."*

`workspace.py` gained `review_dir`, `claude_path` (finds an older course's file where it is until it is tidied),
`review_path`, `module_record` and `tidy`. Every tool that writes now uses them: the content script (its data in
`working_claude\script\`, the page, Word file and instructor notes in `to_review\`), the architecture page (inputs
from `working_claude\`, the page to `to_review\`), the course memory (state and log in `working_claude\`, a pattern
draft in `to_review\`), the knowledge-base tool, the old-course reader, the style copier and the hand-edit detector
(their per-module records to `working_claude\modules\<module>\` for modules in `course\modules\`). The publisher
treats `to_review/` and `working_claude/` as internal. Found on the way: two notes I had written with backslashes in
them made Python print a warning into a tool's output, which broke a machine-read answer - fixed, and every script
now compiles with warnings as errors.

## 4q · The classroom system's own rules (2.21.0, 2026-10-05)

*"Here is the way the course file structure should look, so it can be added to the system properly."* - the owner,
2026-10-05, giving `tablet-system-win/COURSE_FACTORY_PROMPT.md`: *"Give this whole file to the course factory at the start
of a new course ... follow the rules and a course imports with no errors, every task opens on the trainee tablets from its
slide, and every result reaches the instructor and the admin panel."*

Read alongside the rules: the admin importer `admin/package-core.mjs` (read only), which decides what is skipped (`_`
folders except `_course_shell`, `test_`, `.md` `.txt` `.py` `.zip` ...), what is instructor-only (folders and names), what
reaches the trainee (`tasks|handout|documents|assets|assessment/`), and when an import fails (a required link that does
not resolve, a file over 15 MB (6 MB until 2026-10-06), an external script, a key-like string). It is copied byte-identical to
`course-tablet-publisher/vendor/` and run with Node by `check_course_package.py`, after the factory's own checks of
the rulebook's handover list plus L35 and L43. The test builds a two-module course to the rules - it passes both, the
importer would add it as `gas-basic` 1.0.0 with 10 trainee files and the answer key not among them - then breaks it
seventeen ways, each caught. Changed by it: module folders `module01` (not `M01_<title>`), the deck
`presentation\index.html`, the instructor notes reaching the panel as `data-cue` (the importer skips `.md`), module
checks PASSED / NOT PASSED (owner: for understanding, not an official grade - L27 annotated), task pages measured at
1280 × 800 landscape (`check_task_pages.py --viewport` default). The old `check_module_folder.py` now hands over to the
new check; its test was replaced by the new one.

## 4r · 3D where it makes sense, at most half, full quality, and smooth (2.22.0, 2026-10-07)

*"Now he does 3D models almost every slide - cut it down to 50%, better not quantity but quality, use it only where it
makes sense ... it lags a little ... but mainly I love these 3D models."* and *"don't cut quality"* - the owner,
2026-10-07. Read-only look at the pilot first: in its Module 2, nineteen of twenty figures were 3D; each figure kit made
its own renderer with `preserveDrawingBuffer`, worked its soft shadows out again on every frame, drew at pixel ratio 1
(blurry on a tablet), and every figure was built when the deck opened. So: `knowledge/media-and-tasks.json` gained
`three_d` - the cap (half of the presentation's teaching slides, counted from two 3D slides; never a cap on quality),
where 3D fits and where it does not, the words that sound flat, the quality bar, and the performance budget with how
it is measured. `content_script.py` reports `v_3d_share` (must fix), `v_3d_in_a_row` and `v_3d_flat` (suggestions);
the architecture page `p_3d_many`; `check_course_package.py` counts each built deck by the slides' `data-visual` (a
problem over half) and notes, from the module's own scripts, what would lag - more than one renderer,
shadows worked out again on every frame, preserveDrawingBuffer, a pixel ratio of 1 or uncapped, a 3D file over 5 MB.
Nothing in it asks for a plainer look: soft shadows and big shadow maps pass without a word.
Law L46; `course-visuals` and `script/GUIDE.md` say how; `classroom-system.json` names `data-visual` as the factory's own.

## 4s · The classroom rulebook of 2026-10-12: team tasks, hidden answers (2.23.0)

The owner pasted the newer `COURSE_FACTORY_PROMPT.md` (the copy on disk was still the 2026-10-05 one; the importer was
unchanged since 2.22.0). New in it: files up to 15 MB (already followed), **team tasks** (§4b) and "no link into `_`
folders"; the rest was already in `classroom-system.json`. Built: `classroom-system.json` `team_task` and
`task_page.answer_keys`; `check_course_package.py` checks a team task in both places (slide `data-mode`, page metas,
`gb-team`, `scope: 'team'`, `data-team-size`), refuses an answer readable in a trainee page (`data-correct`,
`data-answer`) and a link into a `_` folder, and notes a page that hears the timer but never reports `timeout: true` or
offers "try again" inside the classroom. The factory's own word-for-word marking moved off `data-correct`: a trainee page
marks answers with `data-key = gbKey(id, text, value)` (FNV-1a; `content_script.gb_key`, the page's own function in
the contract, the two checked equal), and `check_script_match.py` reads both. The content script plans a team task (a
task slide's `"team"`: size, roles, scope - validated; never on a module check or the final), shown on the review page
and in Word. `course-task-ux` §9a, `script/GUIDE.md`. Not taken over: the rulebook's optional `tasks/index.html` menu -
L35 keeps the trainee to the one task the instructor opens.

## 4t · A generated picture only after the person described it (2.24.0, nano-banana 1.2.0, 2026-10-14)

The owner: every Nano Banana picture costs about €0.10, and four developers redoing pictures 10-15 times use the
budget up. Until now the factory spawned `nano-banana:image-director` on its own, and that agent retried up to five
times by itself. Now: `knowledge/media-and-tasks.json` `generation_brief` (the flow, eight questions in en/lv/ru, the
price); `scripts/picture_briefs.py` lists a module's places from the approved script, prints the questions with the
script's words as the suggestion, keeps the answers and the agreed prompt, and records every picture made with the
person's words. In `nano-banana` 1.2.0 `generate_image` / `generate_video` refuse without `approved_by_user` (checked
before the key and before anything is sent), log every generation to `~/.config/nano-banana/usage.jsonl`, and return
the count and estimate; `nano_banana_status` shows them; `realistic-visuals` §0 is the ask-first flow, the auto-retry
loop and the 1K draft are gone; the `image-director` agent makes approved pictures once and reports `NEEDS_CHANGE`
instead of retrying. The hand-offs in `course-visuals` (rules, SKILL, GUIDE, the brief schema, the hand-off script),
`orchestration/GUIDE.md` and the `visual-sourcer` agent say the same. Tests: `nano-banana/server/test_nano_banana.py`,
`scripts/test_picture_briefs.py`.

## 4u · The Bloom map (2.25.0, 2026-10-15)

The owner: "My main task is to level up pedagogy - bloom taxonomy needs to be on higher level. That's why we have tablets, because now we can create more difficult and more interesting and more interactive tasks for trainees; before that we used Google Docs / Google Classroom tasks." Nothing in the factory measured the level. Now `knowledge/bloom.json` holds the six
levels (names, plain meaning, example verbs in en/lv/ru), the verbs that signal each (English whole words with their
inflections; Latvian and Russian stems, `$` for a whole word - 'veic$' so that 'veicināt' is not 'veikt'), the weak
verbs, and each of the 14 task types' usual and highest level with how to write it higher. `scripts/bloom_map.py` reads
an ILO's level as its highest clause-leading verb (so a noun in the object is not a verb), a task's from its type or
its stated `bloom`; `course_map` (Stage 2) and `module_map` (Stage 3) return the levels and the findings, drawn by
`make_architecture_page.py` (its own section; never in `problems`, so `--check` exits as before) and
`content_script.py render` (a card, and a level line under each question; never in `all_findings`, so approval is
unchanged). Verbs used both ways (select, determine, check, определить) are left out on purpose: the report says
'not known' and `bloom/GUIDE.md` §2 says how to judge it. Every floor is a suggestion until the owner says otherwise.
Planned next (owner's three-part plan): part 2 the floors as rules; part 3 new task types for *Analyse* to *Create*
(find the fault, spot the mistake in a filled-in permit, build the plan or checklist). Tests: `scripts/test_bloom_map.py`.

## 4v · 20 / 80 in class (2.26.0, 2026-10-15)

The owner: "Now most courses are 80/20 - 80 theory, 20 practical. On paper, in the programmes and IMO model courses it stays as it is, but we want to at least come close to 20/80 - 20 plain raw theory, 80 practical: simulators, active learning theory, self-checks, tablet interactive tasks." Then: "Still you need enough theory ... don't remove existing good theory, because each instructor can skip each slide faster; on paper we have that theory, if someone needs he can read it - but the main teaching activities, how the trainee will gain this knowledge, are in active learning." L5 always aimed at 80 % learner-active, but nothing measured it, and L36's
floors (10 min and 250 words before a self-check; words per minute over every slide) pushed toward long plain
theory. Now `theory-rules.json` `split` holds the aim (0.8), the five slide techniques and the keep-theory rule;
`before_self_check` is 5 min / 125 words; the density counts slides without `"active"` only. `content_script.py`:
`split_of` / `split_html` (a card on the review page, a line per active slide, a print-out in render; an unknown
technique is a `validate` problem; never in `all_findings`). `make_architecture_page.py`: plain = theory minutes less
self-checks, module check and `active_learning[].minutes`; its own section and `a["split"]`, never in `problems`, so
`--check` exits as before; `explore` added to the techniques. The suggestion text names the plain slides with the
most minutes and says to keep every slide - pinned in `test_active_split.py` (no 'remove' / 'delete' in any
language). Three pinned numbers in `test_architecture_page.py` and one case in `test_content_script.py` moved
from 10 to 5 minutes; their behaviour is unchanged.

## 4w · Theory as activity - proposed, then kept or struck (2.27.0, 2026-10-15)

The owner chose step 3 of the 20/80 plan: the factory proposes, per sub-topic, how theory can be taught as activity,
and the operator ticks or strikes each on the Stage 2 page. `architecture.json` `active_learning[]` lines gained
`id`, `subtopic`, `does`, `needs`, `status` (proposed / approved / struck; none = approved, so older courses read as
before), and `technique: plain` with `why`. `make_architecture_page.py`: only kept lines count toward the split;
`plain_all` / `active_all` if every proposal is kept; a waiting card at the top with both numbers and *Copy my
choices*; per proposal Keep / Strike buttons (`aria-pressed`, 44 px), a small inline script that keeps the ticks in
the browser's localStorage (wrapped in try/catch; the page still works without it) and builds the line "Keep: A1.1.
Strike: A2.1." in the operator's language; the script is written only when something waits; nothing is fetched. A
sub-topic with theory and no proposal is a suggestion (`a_no_proposal`). `active_plan.py decide` refuses an unknown
id, an id both kept and struck, or no `--said`, before changing anything; it writes `decided_on` / `decided_said`,
logs Stage 2 rows in FEEDBACK_LOG.md and re-renders the page. Checked by hand in the browser: the buttons, the line,
and the ticks surviving a reload. Not built: step 4 - new creative task types.

## 4x · Five new tablet tasks for the higher Bloom levels (2.28.0, 2026-10-15)

The owner: "Tablet interactive tasks - not only drag n drop, choose e.c., something completely different, interesting and creative." Added as data and checks, like the fourteen before them: `media-and-tasks.json` mechanics
`find_the_fault` (family investigate, hands-on), `spot_the_error` (investigate, hands-on), `build_the_plan` (build),
`timeline` (arrange), `compare` (decide, hands-on), each with its one-box answer form; `bloom.json` levels (4, 5, 5->6,
4->5, 5) - so `lift_text(6)` now names build the plan and says real creation stays with the practical exercise;
`content_script.py` `USES`, `read_answer` (each mis-writing caught in plain words), `answer_items` (what the built
page shows and which are right) and `task_body` (the review mock). Given data - the readings in find the fault,
the events of an incident, the figures in compare - is not counted toward 'was the answer taught' (L36): only the
fault, the stop point and the chosen option are. `course-task-ux` §2a says how each behaves on the tablet. No
tablet engine is written yet - building the task pages is Phase 5 step 6. `test_new_task_types.py` runs each
through validate, the review page, the Bloom map and `check_script_match.py` on a built module.

## 4y · Fast fixes, quality kept (2.29.0, 2026-10-15)

The owner: "i want for fixes to be faster and still quality. like if i find that in module 1-3 is very much free space, i can tell claude to find all free spaces in other modules, and it will not go to 3-4 qa reviews before that, because it takes time and usage." On GAS ADVANCED (FEEDBACK_LOG #61-#93) a
module took 1-1.5 h to build and a minor fix about 30 min: every fix ran the build's whole process - a fixer agent per
module re-measuring every slide at two sizes, the orchestrator re-checking, a whole-course QA, a visual sweep; up to
six agents at once until the PC was unusable (#71, #85) and the usage limit hit (#76); the same wish (S5, S9, S10)
repaired in 19 copies; fixes in generated output lost on rebuild (#88). Now a **fix** mode (`routing.json`
`fix_triggers`) reads `fix/GUIDE.md`, `COURSE_STATE.md` and `STANDARDS.md` only. `scripts/fix.py`: `sweep --find
space | text | overflow | layout | last-slide | kind | words` lists every place in every module, numbered; `propose`
→ `apply --confirmed` → `approve --by` takes words across many modules through each content script exactly as
`content_script.py apply` does (L29) and writes them into the built slides (`data-script-field`, `data-title`, notes
into `data-cue`), listing what would need guessing as hand work, and names a module with its own generator so the
words go there too; `sync-shared` copies `working_claude\shared\` into every module (dry run first, `shared.json` for
another place; L43 kept); `check --kind words | layout | package` runs once on the touched modules; `standard --add
--said` numbers a course-wide wish in `STANDARDS.md`. `knowledge/fix-rules.json` is the authority - thresholds, the
check per kind of change, `never_in_a_fix`, at most 2 agents. `scripts/measure_slides.py` serves the course (never
file://), opens each deck in a hidden Chrome or Edge calibrated to exactly 1280 x 800, presses Start and Next to the
end on a fast virtual clock, and measures each slide with `course-module-ux`'s `audit_compose.js` (ink, empty below,
smallest text, overflow) - the whole 19-module GAS ADVANCED in about 80 s, the same numbers every run, agreeing with
the course's own QA. Three lessons from building it on GAS ADVANCED: several hidden browsers at once left three of four
modules reading 0 % on every slide, while alone they measured the same to the last per cent - so one module at a time is
the default (`--workers` is there, said to be less reliable) and a module that comes back broken or mostly empty is
measured again, alone; measured mid-animation, slides read small text and empty space that the room never sees - so
every entrance animation and transition is run to its end first; and the thresholds are the course's own QUALITY_BAR
numbers (ink 45 %, text 16 px) and S9's "space up and down", not the factory's sign-off minimum (12.5 px). The full
sign-off - the 14 checks in `SKILL.md` *Verify before reporting done* - stays for builds, retrofits and handover.
Tests: `scripts/test_fix.py`.

## 4z · Every picture full screen, one recap for every module, and the person decides the design (2.30.0, 2026-10-15)

The owner: "all images, every picture, illustration, explanitory image e.c., can be clicked and be full screened, and
later you can close it as well"; "each module should of course end in module check, but before it it should be
beautiful summary in same design, like beautiful animation, boxes, main points what to take away from this module,
and all modules should be same closing slide design"; and "if person who uses plugin somehow tells you that he does
not like it, you need to listen to this ... claude should tell person about this risk, but still after person reviews
and tells that he wants his way, plugin listens to that" - "only design ... no course material side".

What was there before: a two-stage tap on card grids (course-module-ui anatomy) and "photographs a trainee identifies
from should be tappable" (course-task-ux) - no viewer for any other picture, nothing in the deck engine, no check. A
`sum` summary grid with no requirement, no place, no animation. L26 already said the operator's request wins - but
fixed the brand and the components as "the style", had no step where the person hears the risk and confirms, and the
checks did not know what the person chose, so the next build or fix flagged the wish and quietly put it back.

- **L51 the viewer** - `course-module-ux/assets/gb_zoom.js` + `.css`, in `course-module-ui/knowledge/design-system.json`
  (copied into every module) and `gb_shell.html`. ES5, starts by itself, delegated: every `img` and outermost inline
  `svg` of 64 px or more. Closes on X, tap outside, Esc, swipe down, Back (history entry), or the active slide changing;
  arrows close it and still turn the slide; touches never reach the deck's swipe. Pinch, double-tap, + / −, wheel, drag.
  Answer surfaces (`[data-key]` / `[data-zone]` / `[data-hotspot]` inside the picture or laid over it, absolutely
  placed) get a ⤢ corner button; a closed `.cmp-card` opens first. Only movement is animated (build/GUIDE.md 9).
  Tried in a browser on a deck: photo, drawing, hotspot frame, each way of closing.
- **L51 the recap** - `theory-rules.json` `recap`; `content_script.recap_findings` (no recap / not straight before the
  module check / twice / 3-6 points: must-fix; a long point: a note); the recap is exempt from the slide word floor,
  the picture note and the 3D-share denominator; `gb_compose.css` section 15 `.slide.dark.recap` (numbered boxes rising
  in, a blue-to-amber rule drawn across, "Next: the module check"; movement only; reduced motion); markup in
  `course-module-ux/build/GUIDE.md` 6a and `screen-kinds.json` `recap`; `check_course_package.py` checks the slide
  before the module check and that every page with a picture loads the viewer.
- **L26 revised** - `knowledge/design-rules.json` (recap, picture-viewer, brand, shared-design, text-size, free-space,
  three-d-share, motion, layout - each with the risk to say; no material rule is in it); `scripts/design_choices.py`
  writes a choice as a standard tagged `[departs from: <id>; risk told: ...]` in `STANDARDS.md` (`fix.py standard
  --departs` too), finds it from any folder, and `check_course_package.py`, `content_script.py approve` and
  `course-module-ui design_system.py check` (state CHOSEN) report it as the operator's choice instead of a problem.
  The same short block sits near the top of all six SKILL.md files (`test_design_choices.py` checks it), and every
  session reads `STANDARDS.md` and the feedback log after `COURSE_STATE.md`.

Not verified: the viewer and the recap on the real classroom tablet and the projector (L39 - the owner's test). Whether
the projector shows an opened picture depends on how the classroom mirrors the instructor's deck.
*§4za-§4zf: the script-compiler branch, its own release numbers (merged into main's line as 2.32.0; its laws renumbered L52-L58).*

## 4za · The deck built from the approved script (2.25.0, 2026-10-15)

`docs/PROPOSAL_SCRIPT_COMPILER.md`, agreed by the owner: the words were typed twice (script, then HTML) and each
module grew its own style file for text and task screens. New lane `compile/`: `compile_module.py` builds
`presentation/index.html` from the approved script and a **build sheet** (`working_claude/script/M01.build.json`:
picture files, layout choices, the module's drawing styles and scripts - kept out of the script so a delivery change
never undoes the approval). The frame is copied from `course-module-ui/templates/gb_shell.html`, the compositions are
the shared vocabulary only, drawings are source in `working_claude/figures/M01/`, every text line is numbered
(`data-i`) for figures that step, hooks come from `window.GB_HOOKS`. It refuses an unapproved script (`--draft`
previews), never overwrites a hand-changed or hand-built deck (`--force`), and lists missing pictures.
`check_script_match.py` gained `--part instructor|trainee` and reads a leading `•` as list markup. Proved on a scratch
copy of the IGF pilot's Module 1 (its drawings moved into figure files): 20/20 screens match, `check_navigation`
clean, `check_course_package` with the classroom importer "Ready", `audit_deck` / `audit_collide` PASS,
`audit_compose` 11/11 composed. Not yet: task pages, module check, start pages. Test: `compile/scripts/test_compile_module.py`.

## 4zb · Compiled as good as hand-built; real photographs; no empty space (2.25.1, 2026-10-15)

A side-by-side of the pilot's Module 1 (hand-built vs compiled, 1280 × 800) found 8 of 11 compiled slides plainer:
the shared `.support` list is 14 px grey (a supporting size), and the hand-built deck had its own reading style, boxes,
a conclusion line, a legend row, inset photos and a photo beside the words - all in one module's file. Those became
shared: `course-module-ui/templates/gb_compose.css` §13b (`.copy`, `.box`, `.call`, `.inset`, `.legend`, `.fill.fig`,
`.two-col.fig-wide`, `.slide.photo.split`, `.act-ico`, `.act-lines`, line states `.cur` / `.lit`; and a fix: a control's
icon inside `.fill` no longer grows to full width). The compiler uses them, bolds the term before " - " / ": ", takes
`boxes` / `conclusion` / `legend` / `inset` / `class` from the build sheet, writes the CC credit with title and
"resized", and warns when a module's style copies are older than the factory's. Round 2: 11/11 slides as good or
better, body text 18.4 px, pictures about 30 % larger; all audits pass at 1280 × 800; at 1024 × 768 drawing labels
(in the drawings) are still under 12.5 px, as in the hand-built deck. Laws **L52** (as many real photographs as
possible - `knowledge/media-and-tasks.json` floors `real_photo_*`, `content_script.py` suggestion `v_few_photos`, labels
in en/lv/ru) and **L53** (no empty space, good padding - `compile/GUIDE.md` §2b, the three audits before showing).

## 4zc · Every drawing whole and clean (2.25.2, 2026-10-15)

The owner's screenshots of the pilot: an engine room poking out through the sloping stern (M01 summary, M02 zones), a
cargo area through a curved bow, a fuel tank and a vent-mast top cut off at the drawing's edge, labels over a deckhouse
and through a box's border. Every existing check was green - all of it is inside one `<svg>`, where none looked.
**L54**. New browser probe `course-module-ux/measure/scripts/audit_drawing.js`: (1) a part whose centre is inside an
outlined closed shape stays inside its real geometry (isPointInFill / isPointInStroke along the part's own outline;
`<use>` of a shared hull expanded; clip-path counts as inside); (2) nothing cut off at the frame or a clipping
ancestor, the line's thickness included, also a part faded out for a later step; (3) every label keeps 4 px to any
shape, line or label and to its own box's edge (in proportion inside a small badge; a leader line may end at it).
Exceptions marked in the drawing: `data-may-cross`, `data-no-contain`, `data-may-overlap`. Safety net
`course-module-ux/assets/gb_fit.js` (in the design-system copy list, loaded by every compiled deck): when a slide comes
up, a drawing whose paint reaches past its viewBox gets a frame just big enough, and a console warning. Test:
`measure/scripts/test_audit_drawing.py` (headless Chrome/Edge on `measure/fixtures/`, skips without one), 13 checks.
Pilot M01 (compiled): 35 findings -> 0 at 1280x800, 1024x768 and 800x1280 after its drawings were fixed (rooms along the
stern, the vent-mast frame, the liquid clipped to the tank, labels moved; valve stems and the thermometer's dots marked).
M02 (hand-built in the pilot, not changed): 64 findings, 5 of them cut-offs that `gb_fit` removes.

## 4zd · The second module compiled (2.25.3, 2026-10-15)

The pilot's Module 2 (20 instructor screens, its deck hand-built) compiled in a scratch copy: its drawings moved into
figure files, the emphasis read from its markup into a build sheet, then every drawing fixed to L54. Result at 1280x800:
words 38/38, classroom importer Ready, navigation clean, `audit_drawing` 64 -> 0, `audit_deck` / `audit_collide` clean,
`audit_compose` 20/20. New build-sheet keys (`compile/GUIDE.md` §2c): `legend` as a line range, `box_alt`, `groups`,
`hooks`, `inset.under`, `aside`, `figure_first`; a room activity with a drawing; a task slide links to the existing page
for its code. Shared look (`gb_compose.css` §13b): a packed stage, `.aside`, a group of small figures as the picture,
`.legend.own-numbers` / `data-n`, a small-projector rule (1024 px: words half the width, a step smaller - nothing spills
or scrolls), a box's heading in bold. `gb_fit.js` adds room only on the side that overflows. Known: at 1024x768 the
drawings' labels, drawn for 1280, fall under 12.5 px - before and after alike; needs labels sized for small screens.

## 4ze · Figures from the figure kit; a missing part made into the kit (2.26.0, 2026-10-15)

The pilot's M02 tank-monitoring slide shipped as four hand-drawn snapshots swapped with `display:none` - no motion,
and a look of its own. The owner: *use the kit; if there is no element in the kit, the AI creates the element, puts it
in the kit, and asks for a merge after the module is complete.* **L55**. New `course-visuals/kit/`: `kit.js` (parts that
draw themselves from a spec, a step engine that tweens values, marks that fire an alarm as their value crosses them -
in the order the value meets them - hold a value at a shut-off and start other moves; a fallback timer so a step ends
when a WebView stops sending frames), `kit.css` (ISA-101: grey at rest, amber alarm, red trip; tokens only),
`SPEC.md` (the format; seven families, two built: instruments, piping and flow), `PARTS.md` (the contract for a new
part), `GALLERY.html` (every part moving; s03, s04, s14 rebuilt from specs), `scripts/check_kit.py` (spec and part
checks), `scripts/kit_parts.py` (list; promote into the factory's kit after the module is complete - prints the git and
merge-request steps, never pushes), `scripts/test_kit.py` (30 checks). Compiler: a `*.kit.json` figure goes into the
page as data with the deck's `.mediabar`, `kit.css`/`kit.js` (+ `assets/kit_parts.js`) load before `GBDeck.init`, each
step lights its slide line; `test_compile_module.py` +8 checks (59 on top of 2.25.3). `design-system.json` installs `kit.js`/`kit.css`.
Orchestration Rule 3: module agents write only their own `kit_parts.js`; the orchestrator promotes at assembly.
Tested on IGF Basic M02 compiled from a copy of the course (s03, s04, s14): steps, lines, slide enter/leave, buttons
steady under the finger. Found on the way, not changed: the shared `.slide.dark::before` watermark reaches 112 px below
a dark slide, which an `overflow:hidden` slide can still be scrolled by (`overflow:clip` would close it).

## 4zf · Every photograph opens, unasked (2.27.0, 2026-10-15)

Aigars's review of the IGF pilot: real photos for the illustrations, and *"images expandable - a lightbox with more
explanation about the photo"*; the operator: *"the factory needs to make it on its own"*. **L56**. New
`course-module-ux/assets/gb_photo.js` + `gb_photo.css` (ported from the definition panel and full-screen figure of the
oil/chemical course, Modules 6 and 10, `course_deck_ext.js`): a tap on any photograph on a slide opens a panel - the
photo whole, the slide's title, what it shows, its credit - and a tap there fills the screen; a `.slide.photo` gets a
48 px Photo button; close button 56 px, the dimmed screen, Escape (one layer at a time); keys and swipes stay with the
panel. `design-system.json` installs both. Compiler: every photograph `<img>` - slide picture, split, inset, and photos
inside drawing fragments and asides - gets `data-about` (the photo's `_photo_meta.json` `description`) and
`data-credit`; a photo with no description is reported; the module's copies are checked like the kit's.
`test_compile_module.py` +7 checks (66). `_photo_meta.schema.json`: the description is now trainee-facing. IGF Basic
M01–M03 recompiled: 12 photographs open, `check_script_match` and `check_course_package` pass. Not done: tap-to-open
*cards* from the same course - automatic cards would hide the lines L53 lights from the figure's steps; they wait for
the script rewrite (claim titles, one lead line) that Aigars asked for.

**L57**, the same day - the operator, at M01 s04 ("five new spaces"): a drawing of real things should also show the real
thing, small and close, to tap. The compiler's `drawn_parts` takes a drawn slide's real things - the term before " - "
in each line (numbered from the kit figure's step whose `line` it is) and the labels the drawing writes on itself (kit
`label`/`text`, SVG `<text>`; an abbreviation alone skipped) - matches photos by the new `shows` field
(`_photo_meta.schema.json`; plural-insensitive, a one-word name only exactly), and puts up to four in a `.photo-strip`
under the drawing, each opening in the L56 panel headed by its part (`data-name`). The pool is the module's photos, then
the course's other modules' (copied in with `copied_from`); `RIGHTS_REVIEW` / `REJECTED` never. A real thing - its last
word in `knowledge/media-and-tasks.json` `photo_things` - with no photo is printed and written to
`working_claude\PHOTOS_TO_TAKE.md` (per-module sections, `## Notes` kept); a photo without `shows` is pointed out; the
build is never blocked. `test_compile_module.py` +11 checks (77).

**L58**, the same day - the operator, seeing the one Viking Grace tank photo under five M03 drawings: *"no duplicate
images - a different one or none, on all modules"*. `photo_id` (the photo's `url_or_origin`, else its bytes) makes a copy
in another module the same photograph; `compile_deck` builds in two passes - first the photos placed by hand (one shown
twice in the module, or shown by an earlier module's deck by hand, is a problem), then the thumbnails, which take only
what no built deck of the course shows (`shown_elsewhere`; another deck's thumbnails give way on that deck's next build).
Fixed in the same pass, from the photo session's measurements at 1280 × 800: the strip and an `"under": "figure"` inset
inside a fragment that is its own row-flex `.fill` (3D model + controls) squeezed the canvas to 0 px - they now go with
the words unless the drawing's box is the compiler's own (`OWN_BOX`); the stage-with-legend layout no longer drops what
goes with the words; `gb_compose.css` `.fill.fig figure.inset img` keeps an inset under a kit figure at inset size (it
grew to ~590 × 440 and squashed `.kit-screen`). `test_compile_module.py` 85.

## 4zg · The course's own pages built; module agents compile (2.37.0, 2026-10-16)

Steps 4 and 5 of `docs/PROPOSAL_SCRIPT_COMPILER.md`. `classroom-system.json:8` said the factory writes
`COURSE.html` and `course_map.js`; no script did, so every course typed them and both start pages of every module.
`compile/scripts/compile_course.py` builds them from what is approved and built: the title from `architecture.json`,
each module's title and minutes from its approved script, the hours from `programme.json`, how the course is named
from `working_claude\course.build.json`, a module's tasks from its built deck's task slides, its instructor files from
the folder. The course title is recorded at the first build and never changes without `--retitle` - it is the
classroom's course ID - also against a hand-made `COURSE.html`. A planned module not built yet is named, never listed;
a task slide whose page is missing is reported; hand-changed pages are kept without `--force`. `course.json` is left
to the importer. On a copy of the IGF pilot: `check_course_package.py` and the importer find nothing wrong with the
built pages, same course ID. Step 5: `build-order.json` steps 8, 10, 11, 15, `orchestration/GUIDE.md` (Rule 3, the
agents table) and `orchestration/workflows/build_course.js` send a module agent through script → approval → build
sheet → compile, writing no HTML and loading no HTML rules: ≈ 80,800 → 38,500 tokens of rules per module agent
(measured, size ÷ 4). `test_compile_course.py` 21 checks.

## 4zh · Every way of answering compiled (2.38.0, 2026-10-16)

Any answer type the compiler could not build forced a hand-made page, which broke the one-look / one-engine rule.
`compile/scripts/task_pages.py` now builds all nineteen of `media-and-tasks.json` - exactly what `content_script.py`
accepts (`BUILT == set(USES)`, asserted). The ten new ones: **complete the sentence** (tap a gap, its choices below; a
wrong gap turns amber with the right words), **choose the action, then the reason** (two columns, one Check),
**scenario** (one part per step, each with its own Check and a Go on), **set the value** (a dial: drag, tap, - / +;
the step from the tolerance or `"step"`; one key per accepted step), **find the fault** (symptoms, a card per part to
turn over, "This is the fault"), **spot the errors** (the document as written, tap a line to flag it, the why after
the Check), **build the plan** (numbered slots, cards that do not belong stay in the bank - `data-key` 1/0 and
`data-place`), **rebuild the incident** (the order, then tap where it should have stopped), **compare** (columns, a
column chosen by its name or any figure) and **operate the panel** (every position of each control, the opposites
known in en / lv / ru or `"states"` in the build sheet; a valve or pump drawn by the figure kit follows the choice).
The engine `gb_answer.js` gained parts and groups (choose, place, dial, stop) and keeps the old markup working. A
place on a drawing may now be a straight-line `path.hit` in a `translate()`d group, or an element id in `"areas"`.

Checkers fixed, each with a test: `check_script_match.py` lets a panel show a control's other positions
(`data-state`) and still catches any other extra word; `check_task_pages.py` reads `data-kit="#id"` as a reference and
leaves the ids inside a compiled-in drawing (`svg.taskfig`) to the drawing; `check_course_package.py` no longer counts
an svg marked `data-no-zoom` (the result ring) as a picture needing the viewer.

Proof: `test_compile_module.py` (a fixture with all ten, keys and markup), `test_task_engine.py` (the page answered in
headless Chrome: 10 of 10 right; 5 of 10 with five wrong and each reveal), and a copy of the IGF pilot: every set of
M01-M03 compiled, nothing left as it is, `check_script_match` clean per module - after its build sheets were given the
task drawings the pilot's hand pages had inlined (the pilot's own build sheets still need that step).

## 4zi · Team task pages compiled (2.39.0, 2026-10-16)

A team task's page was the last set the compiler left as it was. Per `classroom-system.json` `team_task` the page
now carries `task-mode`, `task-roles`, `task-scope` (the slide already carried `data-mode`, `data-team-size`,
`data-roles`) and a bar at the top that `gb_answer.js` fills from the classroom's `gb-team`: the team's name, the
trainee's role, "One answer for the whole team" under scope `team`. No `gb-team` within about 2 seconds: the task
runs alone (it never waits). Scope `team`: the first tablet to finish hands in with `scope: 'team'`, `team`, `by` -
any member, so a team of any size with any roles finishes, and every member reads and answers the whole task.
Scope `member`: everyone's own result. **Proposal to confirm with the classroom app:** the rulebook says the others'
pages show who handed in but names no message; the pages listen for `{type: 'gb-team-done', by, team}`
(`team_task.gb_team_done`). Tests: `test_compile_module.py` team part (both marks, `check_script_match`,
`check_course_package`), `test_task_engine.py` (no team / team / handed in elsewhere / member).

## 4zj · The factory's own words in Latvian and Russian (2.40.0, 2026-10-16)

L19: a course page is in one language. The words the compiler and the engine add - buttons, prompts, the result, the
start pages - existed in English only, so a Latvian or Russian course would have mixed two languages on one screen.
Now `task_pages.py` WORDS, `gb_answer.js` `LANG` (picked by `<html lang>`, still overridable by `GB_ANSWER_TEXT`) and
`compile_course.py` WORDS are in en / lv / ru, asserted complete per language. **PROVISIONAL**: written by Claude and
listed word by word, with the choices made (address, gender-free wording, abbreviated plurals, terms), in
`compile/TRANSLATIONS_REVIEW.md` for Aleksis or a native speaker. Any other language is reported, exit 1 - the page
is built with English factory words, never silently. `compile_module.lang_code()` maps "Latvian" / "Latviešu" /
"lv" to lv (the deck, task pages and start pages wrote `lang="la"`), and `slug()` turns a Latvian or Russian title
into plain letters for the file name. The owner's ruling stands: every course is English unless explicitly not.

## 4zk · The deck's own words in Latvian and Russian (2.41.0, 2026-10-16)

L19, the deck's turn: a Latvian or Russian deck still had Next, Back, All screens, the instructor cue and the landing
card's chips in English beside its Latvian or Russian content. `gb_deck.js` now has a `LANG` table (en / lv / ru,
picked by `<html lang>` as `gb_answer.js` does; `GBDeck.init({text})` still overrides) and puts the words on the
chrome's labels and tooltips, the Start button, the overview and the landing hint - the chrome itself stays copied from
`gb_shell.html` word for word. The compiler no longer passes English words to `GBDeck.init`, and the landing card's
chips are in the course language (`compile_module.py` LANDING); a language with no words is reported, exit 1. The
polite form, as on the start pages. **PROVISIONAL**, listed in `compile/TRANSLATIONS_REVIEW.md` §4-5. Test: a
Latvian deck driven in Chrome (`test_task_engine.py`).

## 4zl · L59 - the ILO map and the knowledge base before any module (2.42.0, 2026-10-16)

Built as 2.38.0 on its own branch beside the task compiler; renumbered 2.42.0 when the two were merged.
Owner: *"before creating any module the AI should have already made the ILO mapping and suggested for
KNOWLEDGE_BASE to be created"*. A session building IGF Module 4 got neither until a follow-up message: the ILO map
was a build step with no file, `script/GUIDE.md` never mentioned the map or the knowledge base, and `"sub_ilo"` on a
question was optional. Now, by rule and by check:

- **Intake suggests a missing knowledge base, unasked.** `kb_tool.py find` with none found prints what one is, which of
  the master folder's files it would be built from (`source_files` and the old course, sorted: programme / model course /
  codes / old course / other), how - the Course Source Processor, which is *not* part of the factory and is said so - and
  what the course loses; `--json` adds the ready pop-up question. `kb_tool.py decision` records yes / built / declined
  (with the operator's reason) in `intake.json` → `knowledge_base_decision`, once. An intake from before 2.42.0 naming a
  knowledge base (or `none`) counts as the decision.
- **The ILO map is a file, made before the split is approved.** `scripts/ilo_map.py` builds
  `working_claude/ilo_map.json` from `programme.json` + `architecture.json` - one row per Sub-ILO per module (a module with
  none: its Main ILO), the Main ILO and topic verbatim, the model-course items under the topic from any
  `*syllabus*.json`. Core fields are rebuilt every time; other fields and keys (the IGF pilot's own tool adds how / where /
  assessed, STCW tables) are kept. `make_architecture_page.py` writes it with the page and shows it, with the KB decision
  (a declined one stays on the page). `--approve --by` records the operator's "next" in `architecture.json` → `approved`
  with the map's fingerprint; refused without a KB decision, with a teaching module missing from the map, a Main ILO not
  verbatim, or a theory-as-activity proposal waiting.
- **The hard stop.** `scripts/course_gate.py` (CLI and module): no architecture, no or stale ILO map, page not approved
  or Sub-ILOs changed since, no KB decision, or the module has no rows → a plain list of what to do. `content_script.py`
  render (of an unapproved script) and approve exit 2 on it; `compile_module.py --init-build` too; `build_course.js`
  pass 2 runs it in a gate agent before any module agent, and the reader now produces the Stage 2 files and the KB
  suggestion instead of free-form `MODULE_MAP.md` / `ILO_MAP.md`.
- **The script uses them.** `script/GUIDE.md` §0 *Before writing*: the module's rows (`ilo_map.py show`), the model-course
  items, the old course's keep / modernise / add, the knowledge base only through `kb_tool.py search`, every fact traced
  in `"sources"`. The review page's **ILO map and sources check** (must-fix, `--despite-findings` possible): a Sub-ILO
  taught on no slide or checked by no question, a question without `"sub_ilo"`, a `"sub_ilo"` the module does not own,
  empty `"sources"`.
- **The IGF pilot is not broken retroactively** (checked on a copy): its `ilo_map.json` reads as the map (67 rows match
  `architecture.json`; the final-assessment row is kept), its intake counts as the KB decision, and M01-M03 stay approved
  with their gaps reported. M04 waits for one command: `make_architecture_page.py --course <course> --approve --by "<name>"`.
- The publisher now sorts `ilo_map.json` and `intake.json` as internal (`course-tablet-publisher/knowledge/platform.json`).
  Tests: `test_kb.py` 61, `test_architecture_page.py` 89, `test_content_script.py` 160, `test_compile_module.py`
  (init-build stop), `test_workspace.py`; `scripts/gate_fixture.py` opens the gate on a test course.

## 4zm · Real photographs and figure-kit drawings on the task pages; a big picture never under the Check bar (2.43.0, 2026-10-16)

Owner's rule: *as many REAL photographs as possible in presentations AND in practical/trainee tasks.* Until now a task's
"figure" had to be an SVG, so a kit chart was drawn twice (IGF M04: a static SVG copy for q03/m06, free to drift) and
a "tap the place" task could not stand on a photo. And IGF M04 finding 12: a read_instrument with a big figure at
1280x800 stacked four options in one column, the page grew to 934 px and the last option sat under the fixed Check bar.

- **A photograph** (`task_pages.py` `photo_fig`): `"figure": "assets/img/x.jpg"` for hotspot, spot_the_hazard,
  read_instrument, label_diagram (the photo is wrapped in a drawing so it gets its label bands), a picture beside
  single/multi choice, above match / categorise / order / cloze / scenario / spot_the_error / build_the_plan / timeline /
  choose_and_justify, and over a `compare` column (`"figures": {"Plan A": "assets/img/a.jpg"}`). Places are the build
  sheet's `"areas": {"words": [left, top, width, height]}` in % of the photograph (there is no drawing to find them on;
  a missing one is reported). The photo's size is read from its header (`image_size`, no library). A file that is not
  there, a photo with no `_photo_meta.json` record, a missing credit, or a picture made by an image model (never for
  what a trainee must recognise) is **reported, never invented**. A tap stays the answer: the picture opens full
  screen only by its ⤢ corner (gb_zoom `answeredOn`); the viewer shows the credit but not the record's description (it
  could give the answer away).
- **A figure-kit drawing** (`kit_fig`): `"figure": "m04_chart.kit.json"` - the deck's own spec, so a chart is drawn
  once. `kit.js` draws it still at the end of its last step (`data-kit-step`; `"kit_step": 2` or a word of a step's
  title for another) with no step buttons, and as a static figure it opens full screen like any picture. Areas are the
  spec's part ids (or the words a part is drawn with); `gb_answer.js` `placeParts` lays each tappable area (56 px
  minimum) and each label-leader end on the drawn part itself once kit.js has drawn it - no box to estimate.
  `"unlabel": "all" | ["P1", "V2"]` takes the words off so the drawing does not give the answer away. Label bands
  use the new `spec.view`. Same spec + different step / unlabel = a separate figure in the page.
- **Layout** (`gb_answer.css`): `data-pic="beside"` (read_instrument, and single/multi choice with a picture) puts the
  picture beside its choices on a landscape tablet (>= 900 px), its height capped to what the screen leaves after the
  header, the question, the room for the explanation and the Check bar (`100vh - 310px`). Nothing is under the bar at
  1280x800 or 1024x768, and the page no longer scrolls.
- Tests: `test_compile_module.py` 166 -> 190 (photo, kit, compare, label, every report); `test_task_engine.py` 49:
  headless Chrome measures both tablet sizes (also proves the old layout fails: 934 px, 766 > 720), the tap-vs-corner
  behaviour, the kit's still step and that every area / leader lies on its drawn part.
- Not proved: the drawn bounds of every kit part type (placement uses the part's own rendered box, tested on tank,
  valve, pump); a real photo at a real tablet (headless Chrome stands in); `compare` pictures are only checked in the
  markup; the Latvian / Russian pages were not re-driven with photos.

## 4zn · What building IGF Module 4 with the compiler found (2.44.0, 2026-10-16)

Source: `M04_BUILD_METRICS.md` §9 (findings 1, 3, 5, 6, 7, 8, 13, 14). Each fix has a test.

- **1 · `check_kit.py parts`**: a part's `css` written as concatenated strings (`'...' + '...'`) is read as css, not as
  drawing code - no more false "fill/stroke set in the drawing". (`STRCAT`; `test_kit.py`)
- **3 · inset on a photo slide**: `gb_compose.css` styles `.photo-copy .inset` (a compact row under the words, image
  <= 16 vh); before, only `.copy` / `.fill` insets were styled and the photo ran at natural size, 74 px off the slide.
  (`test_compile_module.py`)
- **5 · `audit_deck.js`** finishes each slide's finite animations and transitions before measuring
  (`CONFIG.finishAnimations`, default on): the recap's rise-in no longer reads as 23 px "scroll" in a pane where
  animations do not advance. Test in a real browser: `measure/scripts/test_audit_deck.py` + `fixtures/deck_rise_in.html`.
- **6 · `check_navigation.py`** reads the local scripts a page loads (a compiled task page's Back link is wired by the
  shared `gb_answer.js`); a known shared engine (`gb_answer.js`, `gb_deck.js`, `gb_task.js`) counts even where its file
  cannot be read. `test_check_navigation.py`.
- **7 · `bloom_map.py`**: `parent_ids()` - a plain-numbered programme-result row with Sub-ILOs under it (`4` beside `4.1`,
  `4.2`; or `"parent": true`) is the heading of those Sub-ILOs, not a Sub-ILO: no level read, no Apply question asked for
  it, and a question linked to `"4"` serves `4.1` and `4.2`. A dotted row with children (`1.1` beside `1.1.c`) keeps its own level.
- **8 · `design_system.py install`** makes a module folder that does not exist (a new module has none); inside the
  Android project it still refuses and makes nothing; a path that is a file is refused. `compile_module.py --init-build`
  makes the module folder and installs the factory's style files and engines in it.
- **13 · contrast inside a figure**: `audit_drawing.js` check 5 judges each part of a figure-kit drawing (`svg.kit`)
  against what is behind it - the panel, or the opaque shape it sits on: a label 4.5:1 (3:1 large, as rendered), a
  shape or line 3:1 by its fill or its stroke. A part whose colour a rule in `kit.css` sets is the kit's own and exempt
  (the gallery calibrates those); what a course adds (`kit_parts.js` css, inline style) is judged; `data-low-contrast`
  marks a part meant to be quiet. Reported like the other drawing findings by `drawing_check.py` (a build problem). The
  kit's own gallery passes it (a test): `cylinder`'s steel rod became `--faint-d`, the general-arrangement sea backdrop
  is marked `data-low-contrast`.
- **14 · the visual review is required**: `knowledge/build-order.json` step 16 (`visual_review`: a subagent, a
  screenshot of every slide and every task screen at 1280x800, a five-point checklist) and `compile/GUIDE.md` §2f;
  `compile_module.py` prints it under **Next** after every clean build. A credit, caption or full-screen record
  (`.credit`, `figcaption`, `data-credit`, `data-about`) that shows a file-system path or a drive letter is a build
  problem (`credit_path_problems()`), on the deck and on every task page.
- Not touched, by instruction: `compile/scripts/task_pages.py`, `course-task-ux/assets/gb_answer.*` (another agent).

## 4zo · The shared task engine after IGF M01-M03, the compiled answer key, whole-screen corrections (2.46.0, 2026-10-16)

Source: the visual reviews of IGF Modules 1-3 rebuilt as compiled pages ("shared, not the module's"). Each fix is a
check in `compile/scripts/test_task_engine.py` (headless Chrome, 1280 x 800) that fails on 2.44.1 and passes now.

- **Engine (`course-task-ux/assets/gb_answer.js` + `.css`)**: the result screen opens at the top (`toTop()` - the ring
  sat half under the top bar); a part's next step and the feedback are brought between the top bar and the dock by
  `bring()`, never under the sticky bar ("Step 2 of 3" was lost); every choice keeps the letter it was shown with
  (`letterAll()` writes `data-l`; a CSS counter re-lettered a folded step's "C" as "A"); **choose all that are right,
  answered wrong: a right one NOT chosen is outlined dashed green with "Also right"** ("Also wrong" for spot the
  errors), never ticked as if chosen - decided by course-task-ux §0.5 (a tick is what the trainee did right); verdict
  "Not quite – what you missed is outlined in green.". A figure-kit drawing on a task page - a panel's control and a
  drawing to tap or label - is the deck's dark screen (`--deep-2`): on white a closed valve read pale grey, an open one
  solid, the reverse of the deck.
- **Compiler (`compile/scripts/task_pages.py`)**: a picture answered on carries `data-zoom="button"`, so the ⤢ sits on
  the drawing's own corner (it floated at the screen's edge beside a narrow drawing); a drawing to tap narrower than
  `SIDE_AR` 1.8 gets `data-pic="side"` - the screen's height, the explanation beside it (half the screen was empty); a
  list of `MANY` 6+ to order, build, match or rebuild gets `data-many` - the places beside the cards in two columns (8
  rows needed a scroll at 1280 x 800). **Label boxes are sized to their words** (`label_px`, two lines, the tick's room;
  `label_boxes` packs both rows, passes boxes between them, reports what cannot fit; a hand box more than 5 % too
  narrow is reported; the top row keeps clear of the ⤢ button, `CORNER_PX`) - proved on the pilot: M01 m01 and M03 q06
  with their hand boxes removed fit, nothing cut off, none under the ⤢.
- **`course-module-ui/templates/gb_page.css`**: `.scroll th{top:0}` - inside its scroll box a table's sticky head row
  (top 48 px) was pushed down over the first row: the instructor plan and the answer key (found by the visual review).
  The script's top-level `"pass_mark"` wins over the build sheet's (`pass_mark_of`; both and different is reported).
- **The instructor's answer key (`compile/scripts/answer_key.py`)**: `assessment/check_answer_key.html` compiled with
  the task pages from the same approved script - every question in the tablet's order, how it is answered, the right
  answer in the script's words, the feedback, how the pages mark and the pass mark; gb_page look, course language (lv /
  ru PROVISIONAL, `compile/TRANSLATIONS_REVIEW.md` §6); no `data-script` / `data-key`. Listed by `compile_course.py`.
- **The deck (`compile_module.py`)**: a task slide's icon is the gesture its set mostly asks for (`task_icon`,
  `data-icon` choose / tap / drag / order / dial / find / cloze) - all showed one tablet.
- **Corrections (`scripts/content_script.py`)**: a changes file for `propose` may also hold `{"add_screen": {...},
  "after": "s05"}` (or `"before"`), `{"remove_screen": "q05"}` and `{"script_field": "sources" | "pass_mark" | "title" |
  "minutes_allocated" | "operator_facts", "new": ...}` - applied in order on a working copy, shown as understood, applied
  only with `--confirmed`, one FEEDBACK_LOG row each (`3 · M01 · script` for a field); a script field changed after the
  list was made stops apply (content_hash covers the screens only). `test_content_script.py` 161 → 182.
- **Proof** on a scratch copy of the IGF pilot: M01-M04 recompiled, `check_script_match` exit 0 on all four,
  `check_course_package` "Ready", the keys listed on every START_HERE_EXTENDED. M04's two deck contrast findings (slide 3
  kit chart) are the same with 2.44.1 - not from this release.
- After merging, every module needs `design_system.py install --update` (the engine changed).

## 4zp · The module plan compiled from the approved script (2.47.0, 2026-10-16)

Source: the IGF pilot's hand-made `M01_PLAN.html` / `M02_PLAN.html` predated the day's script corrections, and M03-M04
had none (build-order step 14: "one plan per module, stating its allocated and built minutes on its own face").

- **`compile/scripts/module_plan.py`** (new; called by `compile_module.py`, like `task_pages.py` and `answer_key.py`):
  `moduleNN/instructor/MNN_PLAN.html` - instructor-only by its folder, the shared document look (`gb_tokens.css`,
  `gb_page.css`), course language (en, lv, ru; lv / ru PROVISIONAL, `compile/TRANSLATIONS_REVIEW.md` §7). Every block is
  from an approved file, nothing is typed: **the face** - allocated minutes (`minutes_allocated`, with the academic hours
  of `programme.json`) against built minutes (the sum of every screen's minutes), the split plain theory / active
  slides / tasks / room activities (`content_script.split_of`); a mismatch (short, over, or not stated) is a red card in
  words **and** a build problem (exit 1); **what it owes** - the Main ILO and the Sub-ILOs of the module's rows of
  `ilo_map.json`, each with the slides that teach it and the questions that check it; **the running order** - every
  screen: start minute, minutes, theory / active (and the technique) / task / room activity, picture kind, the script's
  notes as what the instructor does, its Sub-ILO; **the tasks** - every set with its code, the slide and minute that open
  it, the pass mark (checks) or "no pass mark", every question with its way of answering, Sub-ILO and wording (the
  answers stay in the answer key); **room activities** with their link hints; **materials** - the architecture's
  `practicals` equipment, the tablets the tasks use, the pictures the script says must be captured at the school;
  **sources** - the script's.
- **`compile_module.py`**: a normal build writes the plan; `--only plan` builds it alone (`--only deck` / `tasks` no
  longer touch it). It is recorded in `compiled.json` like the task pages: a plan changed by hand, or made before the
  compiler, is not overwritten (exit 1) until `--force`. The pilot's two hand-made plans are therefore protected - move
  them to `working_claude/modules/moduleNN/handmade_<date>/` first, or use `--force`.
- Tests: `compile/scripts/test_module_plan.py` (47); `test_compile_course.py` now lists the compiled plan, not a stub.
- After merging, every module whose `assets/gb_page.css` predates 2.46.0 needs `design_system.py install --update`
  (the plan's tables need its `.scroll th{top:0}`).
## 4zq · The figure kit does the drawing work; the figure studio (2.48.0, 2026-10-16)

Built as 2.45.0 on its own branch (`aleksis/figure-kit-auto`), renumbered at the merge with 2.45.0-2.47.0.
Measured on IGF M01-M04: 3, ~10, ~12 and 17 compile runs, nearly all for drawings - label boxes placed by hand in build
sheets (M01 m01, M02 m01, M03 q06), labels overflowing, parts invisible on the dark panel, empty space, 12 px labels,
each found only after a full build. Now the kit and its checks take that work:
- **Labels laid out by themselves** (`kit.js` `layout()` / `solveLabels()`): every part's words are a label
  (`KIT.h.label`) placed clear of every shape, line and other label and of its own box's edge (L54), at the end of every
  step - beside the part, or further out with a leader line. `"text"` with `"to": [x, y]` is a callout. The solver is a
  pure function (`KIT.solveLabels`, `scripts/test_solver.py`) so the 3D kit's label overlays can use it.
- **Task-page label boxes**: one sizing - 2.46.0's `task_pages.label_px` - and `compile/scripts/label_layout.py` places
  them: each box as near its place as the others allow (PAV), order kept, never off the edge or under the ⤢, a full row
  hands its middle box to the other, what still does not fit is reported (the boxes squeezed, never cut off). It fixed
  2.46.0's packing, which could push the last of five boxes 9 % past the right edge (IGF M02 m01).
- **Both panels by construction** (`kit.css` `.kit-light`): a part names the dark-panel tokens; on a light ground they
  mean the light ones. The contrast check stays as the safety net; the gallery passes it on both panels.
- **The 12.5 px floor** (`--kit-up`): shown smaller than 1:1 every kit type size grows by 1/scale (max 2x); boxes, rings
  and rows grow with their words (`fig.fit`); past 1.3x frame growth the words stop growing and SMALL TEXT reports it.
- **Fit**: a drawing that reaches past its frame grows the frame (taller only when the column has room), one lost in its
  frame is zoomed to fill it (max 1.5x; never on a task page, with `view`, an inset photo or `"fit": false`); an alarm too
  long for its log goes on two lines; a panel holds the parts on it.
- **The figure studio** `course-visuals/kit/scripts/studio.py <spec>`: the spec on its real slide (built by
  `compile_module.slide_html` from the script and build sheet), 1280x800 judged and 1024x768 stated, every audit at every
  step, a screenshot - 2-10 s.
- **Checks**: `drawing_check.py` sees a true 1280x800 page (it was 1264x705); `audit_drawing.js` lays a kit figure out
  first, judges a deck's kit figure at every step (`kitSteps`), adds SMALL TEXT, knows an opaque shape hides the line under
  it, and `figure(svg)` audits one drawing.
- **Parts**: promoted from IGF M03/M04 (pipe_section, relief_valve, step_track, coupling, drip_tray, water_curtain,
  detector, flame, curve_chart) and 17 pre-built for M05-M15 from `architecture.json`'s media plans (fan, spray,
  gas_cylinder, push_button, person, sensor, static_charge, fire, flammability, range_bar, hose, manifold, spool_piece,
  tank_wall, spill, wind, tree). `GALLERY.html` has a dark/light switch; `test_gallery.py`: 34 merged parts, 48 figures,
  clean at every step on both panels.
- Tests: `test_kit.py`, new `test_studio.py`, `test_gallery.py`, `test_solver.py`, `test_label_layout.py`.
- **Proof (IGF scratch copy, hand-placed boxes removed):** the studio swept all 32 M01-M04 kit figures - 29 clean first
  time; M02 s15 needed a spec line (`"rows": 2`), M03 s06 and M04 s10 two kit fixes (now in the kit). Then every module
  compiled clean on its first compile with the final kit (4 compiles against 3 + ~10 + ~12 + 17). Deck audits: the same or
  fewer failures than the original course, none in a kit figure. The real course still needs M02 s15 `"rows": 2`.
- 1024x768, stated: the two-col panel shows a figure at 0.54-0.72 of its size; the floor grows its words 1.4-1.9x and
  25 of 32 IGF figures then crowd (labels without a clear place, overlaps). Not judged; the tablet is 1280x800.

## 4zr · 3D and AI pictures planned unasked (2.49.0, 2026-10-16)

- **Why:** IGF M04, M05 and M06 were scripted with no 3D and M03-M06 with no AI picture; the module-level suggestion
  "nothing moves, turns or can be explored" was printed and ignored. Operator: "make it so they add 3D + AI generated
  photos when needed".
- **Script writer** (`script/GUIDE.md`): plans them before the review page - `model_3d` where the lesson is a shape, an
  inside or a layout in space (about one good scene in a spatial module, L46's cap kept), `ai_illustration` where a
  slide sets a scene no real photograph shows (context only, L33; described, priced and said yes to before it is made, L47).
- **Check** (`content_script.py` `propose_3d` / `propose_ai`, words in `media-and-tasks.json` `three_d.fit_words`,
  `not_fit_phrases`, `propose_first_kinds`, `floors.ai_scene_words`): what was left out is named slide by slide, as a
  proposal with the words that made it - never a must-fix (owner 2.18.1). Kept → the script (propose / apply). Struck →
  `"declined": {"3d": {...}, "ai": {...}}` in the script, outside the approved words (the hash does not change).
- **Build** (`compile_module.py`, `compile/GUIDE.md` §2b): a photo slide with no picture file says what it can become.
- **On the pilot:** no proposal in M01-M03 (each has its 3D scene); M04 s10, s06; M05 s06, s05; M06 s14, s06.

## 4zs · What building IGF Module 6 from nothing found, fixed (2.49.1, 2026-10-16)

- **The build:** 84 min, 0 hand edits to HTML, 9 compile runs of which 5 a correct factory would not have needed; 33
  problems logged with file:line in the course's `working_claude/M06_BUILD_METRICS.md` §6. 31 fixed here.
- **Compiler / task pages** (C1-C9, C12, C13, C15, C16): `python -I`; crash-safe build record; `--init-build` from the
  course; `"unlabel": "answers"`; `"not_things"`; inset warning; photo slides in real columns (`.photo-col`) with the
  credit kept; landscape picture beside categorise/order/match; alt text; `.dial-val`; right state on dark drawings.
- **Figure kit / drawing check** (K1-K13, C11): scale and range-bar words through the layout and the audit; parts
  `lamp`, `spark`, `composition_bar`; states `tank.burst`, `gas_cloud.drift`; `text` revealed by a step; EMPTY at the
  busiest step; `studio.py --step all`; contrast after animations settle.
- **Script lane / checkers** (P1-P3, C10, C14, C15, C17): Apply-level numbers; render and `kb_tool` write only on change;
  `audit_compose.all()`; hooks are not unstyled; `measure/scripts/run_audits.py` runs the three deck probes headless.
- **Not changed, on purpose:** per-question Retry (C16) is against course-task-ux §9a (one opening, one result) - the
  owner's call; `two-col` on a photo stays `photo split`, which M01-M06 use deliberately.
- **Proof:** 36 test files; M01-M06 compiled with `python -I` on a scratch copy, the importer ready, `run_audits.py`
  PASS on all six decks at 1280x800. The real course still needs M02 s15 `"rows": 2`.

## 4zt · What the overnight build of IGF M07-M15 found, fixed; every 3D scene answers a tap (2.49.2, 2026-10-19)

- **The build:** M07-M15 and the final assessment built in one unattended run (16:51-19:13), 3D scenes for M04-M07,
  21 factory problems logged in the course's `working_claude/OVERNIGHT_2026-10-16.md` §7. All fixed here.
- **Compiler** (F1, F2, F4, F5, F6, F7, F12, F13, F20, F21, F25): design files checked and updated at every compile;
  `--module final`; final variants `final_a.html` / `final_b.html`; drafts marked and left out of the package; inset spill
  warning (86 words); 3D stage fits its column; `measure/scripts/perf3d.mjs` + `test_perf3d.py`; task photo credit and
  ⤢; long order verdict full width; push button on operate-the-panel.
- **Kit** (F3, F4, F8, F22, `log`): `gas_cloud` figure coordinates; words grow under a photo inset; `push_button` `h`,
  `tree`, `level`, `spill` (approved drawings unchanged: `surfaceY` and its 150 default kept); `person` `labels`; `log` wraps.
- **Script lane** (F9, F10, F15, F23, F24): picture-only re-approval; who proposed / confirmed in FEEDBACK_LOG; stricter 3D
  proposal (`procedure_words`); `ilo_map.py refresh <course> [--module N] [--dry-run]` + `test_ilo_map.py`; approval is
  the operator's own act.
- **3D taps** (operator, 2026-10-19): `media-and-tasks.json` `three_d.interaction` - a tap highlights a part (blue glow,
  framed, named), a second tap or a tap beside resets; course-visuals SKILL, compile/GUIDE.
- **Proof:** 38 test files; IGF M01-M16 compiled on a scratch copy - M01-M06 exit 0, the drafts report only "not
  approved", every drawing clean, importer ready, `run_audits.py` PASS on the changed decks.

## 4zu · One bullet look in every deck (2.49.3, 2026-10-19)

- **Found** (operator, IGF M06 s08): over a photograph every line - heading and point alike - carried the same amber
  left rule, and the points kept a typed `•`; text slides draw points as the `.support` list's blue square.
- **Now:** a `•` line over a photo is `.lead.sub` (the blue square, no rule); the lines it hangs under are `.lead.head`
  (bold, white, a step larger, no rule). A `•` typed in a `.box` is dropped. Photo slides with no `•` lines unchanged.
- **Proof:** `test_compile_module.py` 261; IGF M01-M15 decks rebuilt, 22 photo slides with points measured inside the
  slide at 1920x1080 and 1024x768, no typed `•` left in any deck.

## 4zv · What the pre-merge review of the branch found, fixed (2.49.4 + nano-banana 1.3.2, 2026-10-19)

- **Compiler** (`compile_module.py`): an inset caption, credit or description with a backslash is put under the
  drawing as written (was `re.error: bad escape`); a slide with no words gives no word lines (was IndexError); after
  approval, `--only tasks` / `--only plan` keep `DRAFT_NOT_PACKAGED.txt` - only a deck rebuild takes it away; the
  figures folder and `PHOTOS_TO_TAKE.md` go through `workspace.claude_path` (an older course's `_factory\` is found,
  a missing `working_claude\` is made).
- **`ilo_map.py derive`**: a `"final"` module row sorts last (was TypeError, which also stopped `course_gate.py` and
  `make_architecture_page.py`).
- **`studio.py`**: without 1280x800 in `--sizes` the result is "not measured", not clean; an aborted audit is a finding.
- **`build_course.js`**: the reader runs in pass 1 only - pass 2 never rewrites the approved Stage 2 files; a module
  whose build or QA returned nothing is blocking.
- **Publisher** (`gitpub.py`): git prints paths unquoted (`core.quotepath=false`) and the script writes UTF-8, so a
  course file named `Drošība.png` commits; `push` refuses any branch but `course/<slug>/...`.
  `references/git-workflow.md` no longer describes the removed merge step.
- **nano-banana 1.3.2**: a picture is counted in `usage.jsonl` before its file is written; a usage log that cannot be
  read, or a write that failed, refuses the next generation instead of counting EUR 0. A Pro picture that fails
  (busy, not on the key, no image) is tried once with Flash - one picture, the approved one - and the result says
  so (`fell_back_from`); a key problem is not retried (operator, 2026-10-19).
- **Proof:** new tests in `test_compile_module.py`, `test_ilo_map.py`, `test_studio.py`, `test_publisher.py`,
  `test_nano_banana.py`, and the new `orchestration/workflows/test_build_course.py` (fails on 2.49.3); 39 test files pass.
- **Not changed (stated):** the spending cap still prices every picture and clip flat (EUR 0.10 / 1.50, settable);
  `gemini_take.py take` still moves the newest download without a name filter; the gate report is not tied to the
  staged content; secrets are scanned in text extensions only.

## 4zw · Numbered steps are one list (2.49.5, 2026-10-19)

- **Found** (operator, IGF M11 s04): six numbered steps drawn three ways - step 1 as the headline, steps 2-6 as
  blue squares that also carried their typed numbers, some step names bold.
- **Now:** lines numbered 1, 2, 3 ... in order compile to `ol.support.seq` (over a photo `.lead.sub.step`): every
  step the same size, the step's own number in a navy disc as its marker (`.n`, kept in the words for the match check).
  The compiler half shipped inside 2.49.4's commit; 2.49.5 adds the styles and the vocabulary row.
- **Proof:** `test_compile_module.py` 270; IGF M01-M15 rebuilt, the 12 step slides measured inside the slide at
  1920x1080 and 1024x768.

## 4zx · A selected line always looks selected; a photo never lies on a drawing (2.49.6, 2026-10-19)

- **Found** (operator, IGF M05 s02 and M02 s13): boxes alternated blue and amber by default, and the line a stepping
  figure is on (`.cur`) was amber too - out-ranked by `.box.alt`, so an amber box did not change when selected and a
  blue one turning amber read as the only selection. M02's fire control plan laid its photos on the cargo area,
  covering the bow of the ship, excused by `data-may-overlap`.
- **Now:** every box is blue; `box_alt` (only where the build sheet names it) is grey. `.cur` is amber wash + amber
  ring + amber bar, after every card rule and out-ranking it. `audit_deck.js` "mark": on a stepping slide each
  `[data-i]` line with `.cur` must differ from itself and every other line at rest. `audit_drawing.js` check 7
  "photo over drawing": a real photo painted over drawn parts is a finding (markers drawn after a photo are fine;
  `data-may-overlap` does not excuse it); a shown photo counts as content for EMPTY. M02 s13's photos moved to a
  column beside the hull.
- **Proof:** `test_audit_deck.py` 5 (the old look fails, the shipped one passes), `test_audit_drawing.py` 32 (a photo
  on the drawing found; beside it, or a marker on a photo, silent), `test_compile_module.py` 271;
  the new check flagged M02 s13 before the move and is clean at all 6 steps after it.

## 4zy · The M01 benchmark's compiler gaps: 3D said (L60), EMPTY at the busiest step, the vent mast's tap area (2.49.7, 2026-10-19)

- **Found** (IGF M01 built twice from one script, by hand at 2.24.0 and by the compiler at 2.49.6 - benchmark
  `compiler\METRICS.md`): (1) s05 is `model_3d`, the build sheet gave it a kit figure and the compile passed without a
  word - the compiler never read the kind. (2) EMPTY named s02's rest state, "at its fullest (step 0 of 3)": a part a
  later step brings in waits at opacity 0 and was counted at every step, so every state looked alike and step 0 won
  the tie. (3) A hotspot on a kit `vent` covered only its outlet, so q03 "Vent mast" took a hand-made % box. Behind
  that box, (4): with `"unlabel": "answers"`, two questions on one kit figure shared one drawing (the share key held
  the word "answers", not the answers), so q03 was shown q01's drawing, with "vent mast" still written on it.
- **Now:** (1) a 3D slide whose figure is not an `.html` scene (`[data-stage]`, `data-3d`, `data-scene`, `<canvas>`) is
  a must-fix in the build and a note on the script's review page, "asks for a 3D scene; it has a 2D figure", until the
  slide's entry holds the operator's reason, `"declined_3d"` (content_script `flat_3d`, `build_findings`).
  `--init-build` plans a `model_3d` slide's scene by default: its figure, its scene file and `three.min.js` in
  `"scripts"`, and a `"_figure"` note from M03's `m03_station3d.js` (GUIDE 2b; L46 limits unchanged). (2) each step is
  judged by what it shows (settled), a tie goes to the later step, and the finding says "at its busiest step (step N of
  M)". (3) a `vent` on top of a pipe's upright run lays an unpainted box down the run, so its tap area (and a label's
  leader end) is the whole mast; `"mast": false` / `"mast": <length>`. (4) the share key holds the answers' part ids.
- **L60 (Aleksis, 2026-10-19: "very recommended to build a 3d model at least once where you can in a module"):** a
  script with no 3D slide gets one anyway - `--init-build` gives the best slide (`content_script.best_3d`: one the script
  plans as 3D, else `propose_3d`'s first - a shape, an inside or a layout in space, never a real photo's slide) a starter
  scene entry with a `"_3d"` note on why. A module built with no scene: a RECOMMENDED block in the build and its own card
  on the review page, naming the candidate and why - never a block, never exit 1. Declined with the operator's reason at
  the top of the build sheet (`"declined_3d"`), it is not proposed again; a slide's own `"declined_3d"` takes it out of
  the running. L46 unchanged. Law text: `docs/FACTORY_LAWS.md` L60, `SKILL.md`.
- **Not fixed by this - the benchmark misread it:** M01 s02 without its captions is 60 % blank at its busiest step too
  (all three markers in): the captions fill a real hole, they are no workaround for a wrong check.
- **Proof:** `test_audit_drawing.py` 33 (the M01 s02 scale: EMPTY at step 3 of 3), `test_task_engine.py` 75 (a vent
  mast's tap area covers its pipe run, in a browser), `test_compile_module.py` 284 (L60: the best slide's starter scene, the RECOMMENDED block and review card, declined not again; 2D figure on a 3D slide said in the build
  and on the review page; a kit figure too; a scene silent; `declined_3d` silent, an empty one not; the starter scene
  entry; two questions, other answers, two drawings). IGF M01 recompiled as a copy (benchmark `compiler_fix\course`):
  the s05 finding shows; q03 has its own drawing, no % box, its tap area 56 x 251 px over the whole mast.

## 4zz · The rulebook of 2026-10-19: the result is the last screen (main's 2.31.0, merged as 2.50.3)

The tablet system's project manager sent the next `COURSE_FACTORY_PROMPT.md` (the importer was unchanged). New: after
the result a task page has nothing to press - no "Answers", "Review", "Show solution", "Next task", "Menu" or "Home",
no link - because the trainee tablet has no back button and the classroom shows the answers in the debrief; and a task
moves only between its own steps, never navigating the frame or opening a window. `classroom-system.json`
(`task_page.result_is_last`, `stays_on_its_page`, the handover list), `check_course_package.py` (a link to a file,
`target=_blank`, `window.open`, `location` navigation, and those button labels in markup or set from script are
problems; in-page `#steps`, Next and Previous pass), `course-task-ux` §9a. Tests: seven breaks caught, own steps pass.

## 4zz2 · What the M01 benchmark run 4 worked around, fixed in the factory (2.50.4, 2026-10-19)

Run 4 (factory 2.50.2, `M01_benchmark\compiler_v4\METRICS.md`) passed in 14.4 min with no hand edit to HTML, by working
round six factory problems in its inputs. Each is fixed here, with a test that fails on the old code:

1. **A conclusion on a dark slide.** `gb_compose.css`: `.slide.dark .copy .call b{color:inherit}` - `.slide.dark .copy b`
   (white) out-ranked the callout's own colour, 2.29:1 on blue (s02). `audit_deck.js` "mark" re-reads every line it tried
   before giving transitions back - the last line's background faded back over .2 s while its colour snapped, and the
   contrast check measured the conclusion's dark words on the dark wash, 1.11:1 (s07; a fault of the check, not the
   deck). Fixture `measure/fixtures/deck_call_dark.html`, `test_audit_deck.py`.
2. **The audit summary names what to fix.** `run_audits.py` prints one line per finding - `slide 2 (s02): low contrast b
   "Low-flashpoint fuel" 2.29:1 (need 4.5)`, spills, small text, tap targets, collisions with both elements' words - and
   the probes return the slide's id; `build_module.py` keeps 40 audit lines. `test_run_audits.py`.
3. **`vent` `"mast": true`.** True asks for a mast: the pipe's run under the outlet, else a 60-unit mast the kit draws; a
   length with no pipe under it is drawn too - never an outlet floating in the air. Any other value stops the figure
   (`kit.js`) and is refused by `check_kit.py` before the build. SPEC row updated. `test_kit.py`, `test_studio.py`.
4. **A label that names a feature of its part.** `h.label(..., {at: [x, y]})`: judged against that point, not the whole
   part - a nudge (8 units) is free, any further move off the point gets a leader from it. The `cylinder`'s oil injector,
   gas injector, exhaust valve and piston use it: a neighbour no longer pushes them up the cylinder's side with no line
   (s06). `test_studio.py` (a tank on the left, a room on the right).
5. **`"unlabel": "answers"` on a shared drawing.** `task_pages.py` keeps the answers' words in the spec and lists their
   parts in `"ghost"`; `kit.js` lays them out with every other label and hides them after every layout (a `text` part
   whole, a part's labels and leaders) - the words left stand exactly where the deck has them. Taking them out re-laid
   the rest: on M01 s04, q01's "Fuel tank" moved under the tank connection space. `"all"` still takes the words out
   (nothing is left to misplace); a part's `title` / `tag` (plain text, not labels) still go. `test_studio.py` (M01 s04's
   GA: laid out with the ghosts = laid out in full; taken out = moved), `test_compile_module.py` C4.
6. **No unusable candidate.** `figure_fit.spoiled()` - a part moved outside the frame, or onto a part it was clear of
   (clouds, flames, sprays and text are drawn over parts by nature). A re-fit that is spoiled is never the answer in a
   round, never saved as a fit and never as a `.candidate.kit.json`; the report says why (`usable()`). The kit grows its
   frame to hold a stray part, so the audits had passed s05's lamp at x 635 in a 600-wide spec. `test_figure_fit.py`.

## 4zz3 · Lighter loading again: the Phase 5 rows in full move out (2.50.5, 2026-10-19)

The same move as §4c, for the same reason - moved, never deleted. Since 2.11.0 the *Owner decisions in force* table
had grown to 20 KB of the 55 KB every session reads whenever the skill fires. Each row now keeps its operative rule
(every *never*, *only*, *at most* and limit, the owning file or check) in `SKILL.md`; the row as it stood up to
2.50.4 is in `references/owner-decisions.md`, word for word, one heading per law so a session greps `## L45` and
reads one section, not the 72 KB `laws-in-full.md`. The table's preamble says to read a row in full before working
on its step. `SKILL.md` 55,062 → 43,269 bytes (≈ 13,800 → 10,800 tokens).

The description was 1,610 characters and the skill listing cut it off inside the *NOT* list, the part that keeps
deck and handout requests away from this skill; it is now 962, with the same modes and boundaries and one new
boundary - pptx and Word material belongs to the `novikontas-*` skills (the *Deliberately outside* table already
said so).

## 4zz4 · What the M01 benchmark run 5 worked around, fixed in the factory (2.50.6, 2026-10-19)

Run 5 (factory 2.50.5, `M01_benchmark\compiler_v5\METRICS.md`) passed, but in 9 builds (7 failed) where run 4 took 3. Most
of the failures came from three compiler / kit problems. Each is fixed here, with a test that fails on the old code:

1. **The drawing check gave an unchanged spec a different verdict from one build to the next.** It finished animations
   that end and left the endless ones running, so it judged whatever frame it caught: s03's vent puffs out of a space on
   one build, the engine's own RUNNING over its own piston on another (builds 5-8 changed nothing that mattered).
   `audit_drawing.js` now holds every endless animation in a drawing still at `CONFIG.motionPhases` (9) moments of ONE
   clock across the longest cycle - real frames, so what the kit staggers on purpose (puffs, spray dots, pistons out of
   step) stays staggered; held each at the same phase of its own cycle, a spray's dots piled up and failed contrast - and
   runs checks 1-3 (inside, cut off, text zone) at each; a finding on any of them is reported once, "on 3 of 9 frames of
   its motion". The rest of the checks judge the first moment, held again after EMPTY (its step walk restarts a figure's
   animations), and only animations still live are put back. The kit's label layout (`kit.js` `gather`) measures moving
   parts the same way (5 moments), so a label is placed clear of what a part sweeps: the `cylinder`'s "piston" label, moved
   in off the edge, sat on the moving piston on 5 of 9 frames (s06 - passed by luck in run 5). The `engine` itself:
   RUNNING / STOPPED stands under the lowest point of the pistons' stroke (25) with the kit's clearance on screen, its
   letters measured, and the block grows wide enough for the word (a small engine on a narrow panel ran the word past
   its block). Fixture `measure/fixtures/drawing_motion.html` (the page frozen at three moments by its #hash: one verdict;
   four engines and a cylinder: no self-conflict), `test_audit_drawing.py`. What the deterministic check now reports on
   every build is the spec's to fix - on run 5's s03, the lower ship's vent puffs rise into the upper drawing's space at
   step 4.
2. **Five two-line label boxes did not fit a 2:1 drawing's two rows.** A drawing under its label bands is as tall as the
   screen allows; a 2:1 one is then ~560 of the row's 1240 px wide, and five boxes 185 px wide fitted two to a row - run 5
   placed all five by hand. `task_pages.label_side` widens the drawing's view box on both sides, step by step and only as
   far as the drawing keeps its size, until the boxes fit (`rows_fit`, label_layout's own placing); the label question
   gets that wider drawing (its own name - a hotspot on the same figure keeps the plain one). Not with a box the build
   sheet placed. Run 5's m01 without its hand boxes: three below, two above, clear of the ⤢, every leader on its part
   (`review_sheets.mjs`). `test_label_layout.py` (the run 5 GA, unit and through `question_html`).
3. **`--init-build` wrote no kit starter for a slide planned as 3D.** Declining the 3D meant writing s05's spec from
   nothing, against the Quickstart. `starter_figures(..., fallback=)`: a `model_3d` slide - and the slide proposed for 3D
   unasked (L60) - gets its 2D starter `sNN.kit.json` too; the entry keeps the scene as the plan and says in `"_2d"` how
   to switch (point `"figure"` at it, take the scene files off `"scripts"`, write `"declined_3d"`). `test_compile_module.py`
   (the starter is written, passes `check_kit.py`, and the scene stays named).

## 4zz5 · A vent's puffs rise only into free air (2.50.7, 2026-10-20)

What 2.50.6's deterministic check left on run 5: s03's vent puffs rose into the drawing above on 2 of 9 frames, on every
build. Fixed in the kit, not in the spec. The `vent` measures, at every layout, how far its puffs can rise before they meet
anything drawn above the outlet (`ventRise`: the shapes' real geometry scanned upward across the puffs' width, as the
drawing check judges it - a line, a shape's inside, or the ceiling of a room the outlet stands in) and rises them that far,
up to the 34 they always rose (`--rise` in kit.css `kit-puff`). Where there is almost no air - s03's outlet stood 8 units
under the other ship's keel - the puffs cannot fit and the check still finds them: `figure_fit.py` then adds "fix (vent)"
with the numbers (57 units for the full rise) and what to change (lower the outlet). Run 5's course (scratch copy): with
the vent at y 230 instead of 196 and no hand label boxes, M01 **PASSes** in one build. Fixture `drawing_motion.html`:
`vent-puffs` (a vent 22 under a room: was inside on some frames, now clean) and `bad-mover` (a plain moving disc, the
determinism case the puffs were), `test_audit_drawing.py`.

## 4zz6 · Every slide is one of the owner's layout templates (L61, 2.52.0, 2026-10-20)

The owner reviewed thirteen layout templates on 2026-10-20 (`design/course-layout-templates/`, handoff
`docs/LAYOUT_TEMPLATE_IMPLEMENTATION.md`) and made them the rule for every slide, with the official logo and the
brandbook's colours. Built: `course-module-ui/knowledge/layout-templates.json` (the thirteen, their variants, the rules
as numbers); `course-module-ui/templates/gb_layouts.css` (the look, scoped to `[data-template]` so a deck from before
looks as it did; brandbook colours only - amber is Novikontas Blue; the official `novikontas_logo.svg` top right, on a
white plate on dark slides; Raleway bundled, `templates/fonts/` with its OFL licence), shipped by `design_system.py`;
`compile_module.py` names each slide's template and variant (`auto_template`, `pick_template`), builds the four that
need their own structure (content-in-parts, reference-table, three-content-blocks, compare-two), and checks the owner's
rules - split 55 / 45, a picture beside dense text, never three teaching slides in a row without one, parts instead of
cut words; `gb_deck.js` walks a slide's parts with Next / Back and its tabs. Measured on a sample module with every
template at 1280 x 800 (`run_audits.py`): no low contrast, small text, spill, tap or collision problems; the long slide
that spilled 38 px before is in two parts now. What it costs: a drawing is about 45 % of the slide wide, not 60 % - one
whose labels fall under the floor at that width is reported by the drawing check. Tests: `test_compile_module.py`
`layouts_part` (every slide named; the mapping; the brand colours and the logo; split, dense, sequence, unknown and
unsuitable templates; parts, table, blocks, comparison - all still word for word).

## 4zz7 · Six things a trainee or an instructor saw (2.54.0 - built as 2.52.0 on its own branch, 2026-10-20)

Each found by both benchmark runs of IGF M01 + M02 (`M01_benchmark\workflow_before`, `workflow_after`); each fixed with a
test that fails on 2.51.0.

1. **3D promised after the 3D was declined.** The deck's `data-visual` and the plan's kind came from the script's
   `visual_kind`, so M01 s05 / M02 s09 (kept 2D with `"declined_3d"`) still said `model_3d`. `compile_module.built_kind`
   now says what was BUILT: a 3D kind only for a scene, a photo kind only for a photograph, else the script's kind when
   the figure can be it, else from the figure (a kit with steps: `step_animation`; a flat drawing: `schematic`).
   `module_plan.py` labels the timeline from the same (`slide_visual`). The instructor's cue is the approved words (L29)
   and is never changed: `cue_problems` puts a cue line in "To fix" when it asks the built picture for what it cannot do
   - rotate / turn / zoom / cut open (not a 3D scene), drag, "tap each part" (a kit drawing's parts do not answer a tap;
   its step buttons and lit lines do), tap (nothing to tap). A module figure script that names the slide is trusted.
   Each such line comes with a drafted replacement (`draft_cue`: what the built picture can do, keeping what follows a
   colon), written for the whole module to `working_claude\script\MNN.cue_fixes.json` with the exact
   `content_script.py propose ... --changes` command - propose only shows it, the operator's yes applies it. The
   operator may keep a cue knowingly with `"cue_kept": "<their reason>"` on the slide's build-sheet entry.
2. **Pictures no page shows shipped to the tablets, and `used_in` was wrong.** After every build `ship_only_shown`
   moves each picture of `assets\img\` that no built page, style or script names - with its `_photo_meta.json` record - to
   `assets\img\_unused\` (a folder starting with `_` is skipped by the classroom's importer, `package-core.mjs
   internal()`), and rewrites each shown picture's `used_in` from where the pages show it ("M01 presentation, slide s01").
   Nothing is deleted: named again in the build sheet or a drawing it names (`named_again`; `_` note keys and HTML
   comments are not naming), or picked as an L57 thumbnail, it comes back on the next build. `check_course_package.py`
   leaves `_` folders out of the package's file count, sizes and names like the importer; the publisher's gate
   (`gates.py check_unshown_ai`) refuses an AI-generated picture that no published page shows. IGF: M01 leaves out
   `m01_ai_lng_tank_in_hold.webp` and `m07_portable_multigas_detector.jpg`, M02 seven pictures.
3. **No real photograph reached a task.** `task_photo_notes`: after a build, each tap / spot / label / read-the-instrument
   question whose words name what a real photo of the module's pool `shows` (a thing of two words or more, said whole) is
   listed with the photo and the build-sheet line that would use it - a note, never a block (`build_module.py` lists
   them in one line). IGF M02: the fire-plan photo for q12 and m06 (ILO 2.6).
4. **`data-active` was never written**, so `check_balance.py` failed on every compiled deck. Each block now carries it
   as the L49 split counts: an active slide, a task slide, a room activity all their minutes; a plain slide 0 (owner
   question 2 in §5 is narrowed to slides over 10 minutes).
5. **The figure came after the words** (`check_visual_first` warned on every slide; on a portrait tablet the figure was
   below the first screen). A two-col or flow slide writes its figure first (`.dom-fig`); `gb_compose.css` puts the
   words back first on a landscape screen (`@media (min-width:901px){.slide-body.dom-fig > .copy{order:-1}}`).
   `"figure_first"` slides are unchanged; a hand-built deck has no `.dom-fig`. Proof: every screen of M01 and M02
   photographed by `review_sheets.mjs --all` before and after at 1920 x 1080 and 1280 x 800 - see the CONTEXT row.
6. **A Sub-ILO's parts were not checked one by one.** `content_script.ilo_findings` adds a NOTE (`i_clause_not_checked`)
   for each part of a leaf Sub-ILO that none of its tagged questions asks about. `clauses()` cuts only on ";" and before
   a verb or who / what / where ("... and who on board is involved"), never inside brackets, " - ... - " or after a
   colon; a map row's own `"clauses"` list, when given, is used as it is (additive - no approved map changes). Whether
   it ever blocks is the owner's decision.

## 4zz8 · Shared subject libraries: read first, save back (2.55.0 - built as 2.52.0 on its own branch, 2026-10-20)

Aigars Klūga asked for one shared knowledge base + asset library for the gas courses (GAS BASIC, GAS ADVANCED, IGF
Basic, IGF Advanced); it was built on the company's Drive (`Gas Library`: pictures with provenance, reference PDFs with
distribution, cited facts with the courses' conflicts, glossary, regulations, one search over three knowledge bases).
Decided with Aleksis: the library's content stays on Drive and this public repository gets only the code that uses it;
the factory both reads the library and saves its finds back. Built course-agnostic as **subject libraries** - gas is
the first.

- **Found, never required.** `course-visuals/source/knowledge/subject-libraries.json` (how one is found: the env var
  `NOVIKONTAS_SUBJECT_LIBRARIES`, the library's own `NOVIKONTAS_GAS_LIBRARY`, then the Google Drive default place; which
  rights states may ship) and `course-visuals/scripts/subject_library.py` (`locate`, `covers`, `find`, `contribute`,
  `sync`). None on the computer = skipped without a word.
- **Level 2 is SHARED: 2a the subject library, 2b `resources/`** - the four levels stay four. `resolve_asset.py` asks the
  library's own `find.py --only pictures` (by description, what it shows, teaching purpose, synonyms - never the file
  name); a picture counts as found only in a shippable state, the rest are listed as blocked; a one-word coincidence is
  dropped (the library reports its match strength); an AI picture is held back unless `--allow-ai` (a scene or a
  cutaway) - never the picture of equipment a trainee must recognise. The copy goes in with the library's
  `use_asset.py`, provenance with it.
- **Facts.** At intake the course is checked against the library's subject (`intake.json` *the subject library*), its
  `find` runs before the knowledge base (`build-order.json` step 3, `script/GUIDE.md` §0, `kb/GUIDE.md`), and a CONFLICT
  row is named with the library's `OPEN_DECISIONS.md`, never settled by picking a value.
- **Saving back** (the library's own `tools/contribute.py`, called through `subject_library.py contribute`): a picture
  from level 3 / 4 once packaged in the module, a reference PDF with its distribution, a cited fact or term (into the
  library's inbox as NEW - the owners review), a new course registered so the library harvests its modules. No source
  or no rights = refused; AI flagged. `visual-sourcer` reports CONTRIBUTED; `source/GUIDE.md` §Saving back.
- Tests: `course-visuals/scripts/test_subject_library.py` 21 (fake libraries - no real library needed): absent library,
  rights gate, AI held back, weak match, a broken or older library. Proved on the real Gas Library: "portable gas
  detector" 4 shippable photos + 4 blocked, "type C tank" 1 photo + 2 figures, 4 blocked, the AI cutaway held back,
  "LNG bunkering" 6 photos; with the library switched off the resolver answers as before (exit 3).

## 4zz9 · Physical equipment is drawn as it looks on board (L63 - L62 until the owner's L62 merged, 2.56.0 - built as 2.52.0 / L61 on its own branch, 2026-10-20)

Aleksis approved a plain-vs-realistic mock-up of the figure kit ("yes we like this new kit styling") and asked for it in
the kit itself, on in every deck: no spec option, no per-slide ask. Then: "also do the Parts added from courses", "make
the ship look realistic aswell, look at real images of it", "definitely ... the person", "make this relief valve look better".
- **The materials layer** (`kit.js` `materials()`): one hidden `<svg id="kit-materials">` per page (never display:none),
  holding the material patterns (cladding, brushed steel, machinery paint, cast, deck, rubber, foam, hull plating,
  superstructure white, cloth, protective suit), the shade gradients (cyl, cylv, box, round), LNG, fire, sea, a section
  hatch and two soft-blur filters. The grain is three small canvas bitmaps drawn once per page - an feTurbulence filter in a
  pattern was rendered again on every frame. Colours are the kit's `--mat-*` tokens (`kit.css`); a paint server keeps the
  colours of where it is defined, so a light page has its own set (ids `-l`) and `.kit-light` points at it.
- **Helpers**: `KIT.h.equip(g)` (one piece of equipment: one soft shadow; the drawing check judges it as one object,
  `data-kit-body` in `audit_drawing.js`), `h.body(tag, attrs, parent, {mat, shade, hatch})`, `h.reshape`, `h.flange`.
- **Every physical part reworked** - base: valve (cast body, end flanges, bonnet; positioner and diaphragm actuator, or a
  yoke head and handwheel with `actuator: false`; the ISA bow-tie a light plate, red only on a trip), pipe (stainless,
  mating flanges at every end), tank (cladding, straps, saddles, dome over the pipe that leaves it, LNG in the cut-away),
  exchanger (shell-and-tube, copper coil), pump, engine (bedplate, covers, crankcase doors the pistons work behind, a
  turbocharger with its intake silencer on the end no part is drawn at and inside the engine's room, RUNNING on a name
  plate), vent, well. From courses: all 18
  equipment parts, the ship (from photos of LNG-fuelled ships: plating, sheer stripe, rail, boot-top, bottom paint, bulb,
  rudder, propeller, anchor, white house with windows, mast, funnel band), the worker (navy workwear, real PPE), the fixed
  gas detector (junction box, sensor head, gland, alarm lamp), the relief valve (round angle body, cut-away seat and disc,
  open bonnet with a coil spring, lever), hose ends, manifold block valves and blinds, lamp guards and the Ex fitting.
  Fire, flame, spark and spill drawn as they look (flame colours, a jet fire's lifted blue root, LNG's white vapour fog,
  an arc's blue halo); a dual-fuel cylinder's combustion as plumes along the jets (faint blue gas, bright pilot).
  The gas bottle as it is filled and read: opaque, one paint (its EN 1089-3 shoulder code - N2 black, CO2 grey, air black
  and white quarters - only with `code: true`: the standard leaves out fixed extinguishing systems), a gauge on the valve for compressed gas (needle and bar fall together), CO2 read by weight in kg with its
  pressure left alone and its liquid shown in a window tagged "liquid"; the reading stacked on the plate (number over
  unit), shown only when the steps change that bottle, so a row of bottles stays as narrow as real ones.
- **Layout**: a room's name with no clear place inside (the room filled with equipment) goes beside it; the valve is no
  taller than the ISA symbol it replaces; a shade, a section hatch and a bolt are not measured again, and what does not
  move is measured once per state (not again at every motion phase). Real specs (the M01 benchmark build, 96 figures)
  were drawn new against old: a low tank's saddle feet scale with it (a 40-high tank in a tight hold), its straps are
  surface detail words may cross, the turbocharger stays inside the engine's room, a zone lying on a tank takes deep inks
  (one bigger than the tank keeps the inks it needs over the hull). A second pass over the same figures: the gas detector
  compact and centred on its point (its sensor had poked through a deck), a gas bottle's valve scaled with a small
  bottle, a fan's arrows left out of a duct too short for them, the hull's paint (bottom paint, boot-top) surface detail
  words may cross, and a leader line keeps the full clearance from every word, the words drawn in parts too.
- **Words on light equipment**: a room's name or a caption over a light surface (the tank's cladding, the white
  superstructure, machinery paint) is printed in dark ink as on a nameplate (`kit.js` `inkOn`, once the labels are
  placed), not in light letters with a dark halo.
- **`audit_drawing.js` twice as fast, the same findings**: a bounding-box test before each point-in-shape test, one inverse
  matrix per shape per pass, a body's shade / hatch / bolt judged as the body (`kitCopy`). IGF M03 s15 (8 steps, six
  flowing pipes) audited in 27 s (56 s before, with half the shapes); `test_audit_drawing.py` 37 pass.
- **The rule** (`SPEC.md` "Rules of the look", `PARTS.md`): a part declares `look` - `equipment`, `screen` or `diagram`;
  equipment draws its bodies in a kit material; screens stay ISA-101. `check_kit.py parts` enforces it (`test_kit.py`).

## 4zz10 · Builds that do not overload the PC and do not judge again what did not change (2.57.0, 2026-10-20)

Aleksis: "how to make builds stop taking so long on a busy PC". The 2.56.0 integration day showed two causes: several
processes each starting their own hidden browsers (a test suite, a module rebuild and two test re-runs at once - CPU at
99 %), and every rebuild judging every slide again when one to three had changed.
- **One pool of hidden browsers for the whole computer** (`course-factory/scripts/browser_slots.py`, its Node twin
  `course-module-ux/measure/scripts/browser_slots.mjs`). Every place that starts a hidden Chrome or Edge - the drawing check,
  figure_fit and the studio, run_audits, measure_slides, review_sheets.mjs, perf3d.mjs and the tests that drive Chrome -
  takes a slot first: a lock file `%TEMP%\cf_browser_slots\slot_N.lock` made with exclusive create, holding the PID, held for
  the browser's life. A slot whose PID is not running (a crash, a kill) is reclaimed at once; one not touched for 5 minutes
  (its holder's PID reused by another process) too. Slots: half the cores, at most 8, `CF_BROWSER_SLOTS` to set it. A slot is
  held for one browser and never while waiting for another (the studio's two to four runs per figure now each take their
  own, in threads), so no process waits on itself. `test_browser_slots.py`: two processes of four threads never hold more
  than the slots, and do use all of them; a killed holder's slot reclaimed; Node waits in the same queue.
- **A slide or task page judged clean is not judged again until something it shows changes**
  (`course-factory/scripts/check_cache.py`), as figure_fit already did for figures. The fingerprint is the slide's section
  (or the whole task page), its place in the deck, the deck around it, every file of `assets\` but the pictures, every file
  the slide names (its photos, a 3D scene and what that names), the checker's own scripts, the window size and the browser.
  The drawing check (`drawing_check.check(..., cache=, full=)`, from `compile_module.py`) keeps only the changed slides in
  the page (the 2.56.0 slicing, now a list of slides); the audits (`run_audits.py --cache --full`, from `build_module.py`)
  load the whole deck and measure only the changed slides (`AuditDeck.all(only)`, `AuditCollide.all(only)`,
  `AuditCompose.all(only)` - compose still walks every screen with Next). Only clean results are kept, in
  `working_claude\_build\MNN_drawing_clean.json` / `MNN_audits_clean.json`: a slide with a finding, a compose REVIEW screen,
  a page that did not finish, a run that aborted or whose browser counted the slides differently from the fingerprints is
  judged again next time. `build_module.py --full` judges everything (the figures too). `test_check_cache.py`: a defect
  planted on one slide re-checks that slide only and IS found, and again on the next run; a changed photo re-checks its
  slide, a changed design file every slide; the audits the same.

## 4zz11 · A build's time measured, and the probes' own work cut - every check finds what it found (2.61.0, 2026-10-21)

Aleksis: "why do builds wait so long on build_module.py". Measured first (`CF_TIMING=<file.jsonl>`: every hidden-browser
run writes its real seconds and its page clock, `course-factory/scripts/cf_timing.py` adds them up; CPU profiles): the
waits under `--virtual-time-budget` are nearly free, endless animations or not; the time is the drawing probe's own work -
`getPointAtLength` was 21 of 53 s on IGF M02's deck, every outline sampled again at each motion phase and step.
- `audit_drawing.js`: a shape's outline in its own units is kept while its geometry is unchanged (attributes, the CSS
  geometry properties, its length, the number of points); only where it lands on screen is worked out each time, the
  screen matrix once per shape. `CONFIG.outlineCache: false` samples every time. `test_audit_drawing.py`: 66 findings on
  the defect fixtures identical either way.
- `review_sheets.mjs`: a wait ends when every page timer the old fixed sleep let run has run and two frames are drawn -
  never later than the sleep; gb_zoom's scan, which only adds, runs at once. `--fixed-waits` is the old way.
  `test_review_sheets.py`: the same screens, pictures and grading either way.
- `run_audits.py`: the viewports side by side (`--jobs 1`: one after the other); `figure_fit.fix_tasks`: the task pages
  side by side.
IGF M01 / M02 `--full` on a scratch copy, interleaved: median 82 -> 57 s and 183 -> 112 s, the review sheets halved; every
build log, review fingerprint and grading the same, and a planted engine out of its room found word for word
(`Desktop\M01_benchmark\speed_test\SPEED.md`). Not done: scoping `getAnimations()` (0.13 s of 53 s) and letting the
drawing check skip a figure figure_fit judged (another frame and timing - not provably the same findings).

## 4zz12 · Never the same look twice in a row; a larger logo; no blocky photographs (L62, 2.62.0 - the owner's 2.53.0 on main, 2026-10-21)

The gas course's Module 1, the first built in the templates, came out with 29 of 33 slides as content-in-parts with
the picture on the right - its build sheet asked for that template on every slide, and nothing stopped a run. Its
photographs were 350-1100 px (s01: 400 x 293) stretched to ~500 x 600 px at 1280 x 800, and the logo's artwork was
about 55 px wide inside its clear space. Now: `layout_key` (shape and ground), `layout_options` (the ways one slide can
be built that hold its words and picture), `choose_layout` (its own unless it repeats; else unlike the last three);
the dark ground only for a photograph or a kit drawing (the module's own step widgets lost their controls on dark:
2.06 and 1.07 contrast on s07, s15, s19, s26 - caught by run_audits, fixed); the figure-stage variant `figure-top` for
photographs up to 110 words; a build problem if two neighbours still look the same; `enlarge_photos` (Pillow,
Lanczos + UnsharpMask, at most 4x, to 1600 px, originals in working_claude/photo_originals/M01/, under 800 px listed);
the logo box sized for 10.5 vmin of artwork, and on dark (blue) or photo slides the white version (`plugin/resources/brand/novikontas_logo_white.svg`, the official paths with the one colour switched), no plate; a light panel stays white on a dark slide; the recap fits six take-aways
under the template's top line (41 px spill before). Proved on a copy of that module: 33 slides, no neighbours alike,
five looks among the photographs, `run_audits.py` at 1280 x 800 and 1024 x 768 with no contrast, size, spill, tap,
collision or scroll problem. Tests: `test_compile_module.py` `variety_part`. Merged on top of 2.61.0: the kit's realistic
look (4zz9) is L63 now; the template recap keeps 2.60.0's compact spacing under 780 px height.

## 4zz13 · Caught before the build; photographs found large; a rebuild is a fix; the gold standard (L64, 2.65.0, 2026-10-26)

The owner asked how to cut a build's time and usage with the quality the same or better, chose two of the answers ("build
points 1 and 2"), then: a rebuild or a fix goes the fix lane, and the gold standard is 30-40 minutes a module plus 20 for
fixes. (1) `compile/scripts/precheck.py` - a second, standard library only - finds what would fail a build from the files:
a missing figure / figure_b / aside / inset or a photograph missing inside a drawing, an unknown template or variant, a
photograph under 800 px without `"low_resolution_ok"`, a teaching slide over `DENSE_WORDS` with no picture, three
teaching slides in a row without one (MUST); a template forced on 3+ slides in a row and photographs of 800-1599 px
(notes). 3D posters are skipped. `build_module.py` runs it before the figures stage (`--no-precheck` skips it); on the
gas course's real M01 it found the 11 photographs under 800 px that L62 had enlarged into blur. (2)
`course-visuals/scripts/image_size.py` - a picture's pixel size from its own header (JPEG, PNG, WebP, GIF; checked against
Pillow on 42 photographs) and `found_size`, the size it was FOUND at (the kept original while the shipped file is still
L62's enlargement); `check_assets.py` warns under 1600 / 800 px; `visual-sourcer` looks for the original file at 1600 px
or more; `asset-pipeline.json` `photographs_min_long_px` / `photographs_floor_px`; `enlarge_photos` refreshes the kept
original each time. (3) `fix.py rebuild` (pre-check, `design_system.py install --update`, compile, one layout and one
package check; drawing findings named for `build_module.py` alone - ~20 s on the sample course); `routing.json`
`fix_triggers.rebuild_words` / `_built`, `test_routing.py` `route(..., built=True)`; `fix/GUIDE.md` 3b. (4)
`scripts/cf_timing.py` `clock_start` (at `--init-build`, or the first build run), `clock_pass` (the first PASS's
`TIME M01: ...` line, once), `fix_line` (a rebuild against 20 min); `build_course.js` asks the builder for the TIME line
and returns `gold_standard` (a workflow has no clock of its own: `Date.now()` is not allowed there). Tests:
`compile/scripts/test_precheck.py` (33), `test_routing.py` (87), `test_build_course.py`. (5) Run on the real gas course: almost every small picture is the old course's own (M01 10 of 11, M09 24) - so: A still rendered from the module's own 3D model is a note (render it again larger); a picture from the old course has no larger original, and the stop says so - find a larger photograph of the same thing; a REBUILD (`fix.py rebuild`, `precheck.py --rebuild`) is never stopped by the small pictures a module already has - they are notes (the gas course has 100+ old-course pictures under 800 px across its 22 modules). (6) The whole-course workflow builds the biggest approved module first (the most minutes in the approved table) in a rolling pool of `args.wave`: the next build starts the moment one ends - no wave waits for its slowest module; a QA agent holds no place, a fix round does. (`build_course.js` `ORDER`, `place`; the IGF M01-M03 run had M02 as the long pole of its wave.)

**2.65.1 (2026-10-26) - the fix lane's first real rebuild** (the gas course's Module 1, after its 8 small ship photos
were replaced by Wikimedia Commons originals of 2400 px). (1) The rebuild's one check was the fix lane's 16 px "text
bigger" sweep: it called 14 slides small that the build passes (its floor is 12.5 px, a kit figure's 16) and did not
look at 1024 x 768, where 6 slides scrolled. It is now the build's own audits at both sizes; a failure names
`build_module.py` for that module. (2) `build_module.py` on a module built before (its deck exists) is a rebuild for the
pre-check: the small pictures it already has are notes, not a stop - the 3 old-course pictures of M01 s22 / s23, which
have no free replacement anywhere, would otherwise have blocked the very build fix.py names. (3) A fix under a minute
says its seconds ("0 min" read as broken). Tests: `test_precheck.py` 35.

## 4zz14 · The speed round: a module in 19 minutes (2.66.0, 2026-10-26)

The owner: *"now I need to optimise as much as I can in this course factory"*. Measured on the same module twice - the gas
course's Module 2 (57 screens, 80 min), built from its approved script on a copy, by one Sonnet builder with the
workflow's own builder prompt, its photographs already in the folder: on 2.65.0, **30 min** from the starter build sheet
to the first PASS (33 min of builder time, 384 k tokens, 84 tool calls); on 2.66.0, **19 min** (22 min, 346 k tokens,
93 tool calls). What the first run lost, fixed: (1) the starter drawing was 640 wide, but since the templates (L61) the
figure column shows a drawing 456 px wide at 1280 x 800 and 345 px at 1024 x 768 - at 0.54 its words fell to 9 px, kit.js
grew them into each other, and all 21 starters were redrawn before run 4: `STARTER_W` 416 (the same shape), and
`STARTER_MIN_CELL` so a part and its words always fit their cell (`starter_cells`); SPEC.md, CATALOGUE.md, compile/GUIDE.md
say 416 x 254. (2) the layout retry ran 447 s on the slides of drawings about to be redrawn: `build_module.py` builds no
layout round while drawings are open (`drawings_open`), and says the slides it holds. (3) `"parts"` beside a picture is
content-in-parts without naming the template; on a slide with no picture it is said (`pick_template`). (4) a picture the
build sheet names that waits in assets/img/_unused/ is there for the pre-check (`precheck.parked`) - the compile brings it
back. (5) a builder reads the Quickstart by its path, never SKILL.md (48 KB, every mode's router): the gate reports the
skill's folder (`skill_dir`, found by Glob) and `build_course.js` `LEAN` sends it; a gate with no folder falls back to
loading the skill. (6) CATALOGUE.md `MUST KNOW` lines, never clipped: the gauge's ticks / every (three builds lost to
"0 0 1 1 2"), the gas bottle placed by its base. (7) Two control characters in precheck.py (a `\b` written through a
shell) had silently disabled its 3D-poster rule and its .pptx origin: fixed, and no tracked file has one. (8) The kit parts the second run asked for (owner: "do the kit parts next"): **a drag** - `KIT.h.drag`, one invisible focusable area a finger, the mouse or the arrow keys move, the press and the keys never reaching the deck (tested in Chromium: 0 keys reached the page, the next step puts the part back); `curve_chart` `point.drag`, `point.curve: "all"` (every curve's value beside its own dot, only inside each curve's data) and `yaxis.log` (decades; between points straight in log); `scale` `markers[k].drag` (upright and across, its word reading the value); the new `molecule` part - a cargo's structural formula by name (methane ... butane, ethylene, propylene, butadiene, VCM, ammonia, N2, CO2, water) or as atoms and bonds, `build` bringing the skeleton then the hydrogens, centred and grown to its box. `audit_drawing.js` counts a kit group marked `data-kit-fills` by its box (a formula is atoms with air between, as a pipe's bends). The compiler's cue check sees a draggable kit figure (`figure_can`): a cue that says drag needs no `cue_kept` there. Studio clean on both panels at both sizes (the log chart with two cargoes and the cursor; propane building); a compiled deck with both passes every audit at 1280x800 and 1024x768. CATALOGUE.md 58 parts, MUST KNOW for each, still under 15 KB. Left for the
next round (the second run's report): the fact check reads step titles ("3 H"); a generic word in a photo's `shows` asks for it on unrelated
questions. Tests: test_starter_figures, test_compile_module 463, test_precheck 36, test_build_course, test_kit.

## 4zz15 · Starters from the slide's words, a drawing library, spills fixed by the build, photos while the script waits (2.67.0, 2026-10-26)

The owner, after the 2.66 round: *"do all"* - the seven items left by the timed gas M02 build. (1) **The starter picks the
part the words ask for** (`starter_special`): a slide about formulas, molecules or atoms that names cargoes starts with
their `molecule`s (in the lines' order, one step each; side by side, or one above the other in the figure column's shape
when long chains would get bonds under 34); a slide about vapour pressure / boiling points / curves starts with a
`curve_chart` of the cargoes it names - their points ONLY the temperature / pressure pairs the slide states (a cargo with
fewer than two is left out and named; no stated points: the grid starter - gas M07 s07, a ppm slide, had got two
made-up curves); `yaxis.log` when the pressures span decades; a cue that says drag makes the point (`point.drag`) or a
scale's marker draggable. (2) **A slide whose own layout spills is put in parts by the build** (`build_module.spilled_own`,
`parts_out`, `compile_module.wants_parts`): the audit's "scrolls" / "spills" on a slide the compiler laid out itself (no
"template" asked, not moved for L62, a picture, two lines or more) is recorded in `_layout_avoid.json` and built again in
the same build with its words in parts; a template asked by name is never overruled. (3) **The figure library**
(`compile/scripts/figure_library.py`): a module that passes keeps its kit drawings - in the course's
`working_claude/figure_library/` and this computer's (`~/.novikontas/figure-library`, `NOVIKONTAS_FIGURE_LIBRARY`) - and
`--init-build` starts a slide that names the same things (two or more, 60 % of its own) from that drawing, its steps made
again for the slide's own lines; a course in the temp folder (every test's) never reads or fills this computer's library.
(4) **Photographs while the script waits** (`build_course.js` `photoPrep`): a script written in a run gets one Sonnet agent
that places its photographs with their rights records and lists them in `working_claude/photo_candidates/MNN.md`; the
builder uses them first. (5) "3 H" is three hydrogen atoms, not three hours (`facts_in`). (6) A photo's one-word "shows"
that says how a thing is ("pressurised") never asks for it on a question (`DESCRIBES`). (7) Measured: three modules built at
once on a copy of the gas course (M02 43 screens, M07 24, M15 11 - the workflow's biggest-first order, the lean builder
prompt): M07 **11 min** (2 runs), M15 **16 min** (7 runs), M02 see CONTEXT. What that run found, fixed: the starter curve
rule above; the builder prompt says the photo list exists only when photographs were found during approval;
`check_balance.py` crashed on a half-minute slide ("0.5"); the pre-check's size note says it judges the size a photograph
was found at; CATALOGUE `MUST KNOW` for the valve (`state: false` hides OPEN / CLOSED - three runs on M15); the Quickstart
says a question's drawing has a frame of its own (about 880 x 550) and a ghost label is still laid out. Kit, found on the
way: curve names are labels the layout keeps clear of the reading point; a molecule's bonds across and down may differ by
up to 1.6 times to fill its box. **Photo tiles, and Module 2 measured (same evening).** `"tiles"` on a slide: the compiler builds several photographs as one picture, each opening full screen with its record and credit (`tiles_figure`, `gb_layouts.css` `.lt-tiles`); `"tiles_as": "strips"` stacks numbered cuts of one document - gas M07's builder had hand-written five such fragments; the pre-check judges tiles like any photograph; `--init-build` puts the module's photographs on the slides their records name (`link_photos`: one is the figure, several the tiles - gas M02's 24 went on none and were moved to _unused). The three-module run's M02 took 124 min (12 runs) on a computer shared by three builders, the tests and another session (single runs of 257-471 s, one compile timed out at 900 s) - and the first version of the word-picked starters gave it seven placeholder curve charts and four wrong molecule sets: the curve rule now needs points the slide states, and the molecule rule reads only the slide's title and picture for formula / molecule / structural / atom - on all 22 gas modules it now picks 4 slides, each a formula slide. test_tiles 9. **The training app and the fix lane (same day).** (a) The task engine (`gb_answer.js`) sends each question WHOLE to the classroom - `{t, ok, a, c, w}` (asked, picked, right, why; 90 / 120 / 120 / 400 characters) and `detail: 2`; a blind final sends a, c and w empty (`classroom-system.json` result). A read-only check of github.com/silkansraivis3-tech/novikontas-training-app (HEAD 09eda10) found the import works (its package-core.mjs is the factory's, byte for byte; the full gas course imports, 23 modules) but its debrief re-read the screens when only `{t, ok}` came: gas M07's 4 questions became 11 items, the why always empty, for the trainee and the instructor. The app's side - believe a page that sends `detail: 2`, no 'YOUR ANSWERS' overlay and no answer buttons after a task (the owner: "after tasks only one page is visible, all answers and all questions, no buttons"), and `gb-team-done` to the page - is a patch for that repository, not in this one: factory-work/_app_patches/training-app-factory-results.patch. The handout already closes when the task does, and says "Back to the task" while one is open. (b) A labelling question's valves print no OPEN / CLOSED, and the engine ends a leader where it reaches its part (the point of the part's box nearest the label), not at its middle across its words (gas M15 m01: three runs). (c) `fix.py rebuild` compiles and audits the modules four at a time. The owner's fix sessions ("a build in 50-60 min, a fix 40-50 min; one slide in every module 1-2 h"): the gas course's session, read - 47 helper agents, `fix.py` used by none for a fix; every change a full build_module round (e.g. 54 min / 9 builds to rebuild one module, 193 min / 17 builds for one continued build) and a visual-review agent after each (6-19 min); and the computer still runs course-factory 2.53.0, which has no fix lane for a built module. Also (the same afternoon): the studio's contact sheet draws at the templates' figure column (504 / 392 px, was the old two-col 682 / 443 - words passed there and failed the build); a question that taps or reads a drawing gets no label bands (they are a labelling question's; gas M15 m05 was 54 % blank because a labelling question shared its drawing); the Quickstart line on a question's drawing corrected. Left for the next round: a recipe for slides of photo cuts that tap to reveal (M07's
builder hand-wrote five fragments, about 8 minutes); the starter's frame for content-in-parts slides (534 x 228 at 1280).
Tests: test_figure_library 7, test_precheck 39, test_compile_module 466, test_starter_figures, test_build_course,
test_check_balance.

## 4zz16 · Better pictures at the same speed: photographs made sharp on this computer, 3D that stands and never judders (2.68.0, 2026-10-27)

The owner: *"how we can keep speed but upgrade quality? 3d models so it looks better but not lagging? how to upscale
existing photos with plugin without other outside AI use?"* - then *"do both, download is ok"*. (1) **The local enlarger**
(`course-visuals/scripts/upscale_photos.py`): Real-ESRGAN (ncnn-vulkan v0.2.5.0, model realesrgan-x4plus, ~45 MB, BSD-3)
unpacked to `~/.novikontas/tools/realesrgan/` (`NOVIKONTAS_UPSCALER` overrides) enlarges a module's photographs under
1000 px four times on the graphics card and the result is brought to 2400 px on its long side - nothing leaves the
computer. A picture whose name or description says words or numbers (page, sheet, SDS, table, label, sign, screen, panel,
gauge, chart, diagram, plan, document, scale, dial, meter...) is never enlarged - the enlarger invents detail and would make
the letters sharp and wrong; `"ai_enlarge": false` on a record keeps any other out. It works from the original the compile
keeps (`working_claude/photo_originals/MNN`), writes `"enlarged": "Real-ESRGAN realesrgan-x4plus on this computer, from W x H
to W x H (date)"` on the record, and does nothing twice. `--list` says what it would do; `--check` whether it is installed
(exit 3 with the link when not). Measured on a copy of gas M02: about 40 s a photograph on the Intel graphics; clearly
sharper than the plain enlargement; photographs of 1000 px or more were slower (73-172 s) for little gain, hence the
limit. (2) **The pre-check** judges an enlarged photograph at the size it was found and says it was made sharp locally -
"a real larger photograph would still be truer" - never a stop; a small photograph with the enlarger installed gets the
hint to run it. (3) **The whole-course workflow** (`build_course.js` `photoPrep`) runs it on the photographs it finds while
the script waits for approval. (4) **kit3d, better looking at no cost while it turns**: a model with no floor of its own
(no part covering 60 % of the scene's width and depth at its bottom) stands on an unseen ground that shows only its
shadow (`ShadowMaterial`, darkness `ground_shadow` 0.24, `"ground": false` leaves it out) - the shadows are worked out
once, so turning costs nothing more; the 7 example scenes all have decks or floors and are unchanged. A slow tablet: while
the model moves its frames are timed, and 20 in a row averaging over 45 ms draw it one step less sharp from then on (pixel
ratio 2 -> 1.5 -> 1; `window.__scene3d.dpr`) - a new drawing buffer costs up to a second, so it never goes back up.
Tests: test_upscale_photos 10 (a stand-in enlarger, so it runs anywhere), test_kit3d +4 (the ground under a floor-less
model, none over a deck, a slow screen steps down, a fast one keeps 2), test_precheck 39, test_smoke3d 15, test_perf3d 13,
test_build_course.

## 4zz17 · What a 16:9 screen showed, and the trainee's handout (2.69.0, 2026-10-27)

The owner's three screenshots of the gas course's Module 1 (built on 2.65): *"all 3d models is almost invisible with these
buttons to close up detail, also table is awkwardly layouted, also picture you cannot see ship at all, bad center - dont
change gas basic for now, just fix course factory so in future courses its not the problem"*. Measured on a copy: the
screenshots were 1280 x 720 CSS pixels (a 1920 x 1080 laptop at 150 %, or a 720p projector), and the build had only ever
looked at 1280 x 800 and 1024 x 768 - s15's table cut its headings and its step names at 720 and nowhere else. (1) **The
build's audits run at 1280x720 too** (`build_module.py`, `fix.py rebuild`, GUIDE, the workflow); the part tabs are 44 px
there (`gb_layouts.css .lt-tab`, they were 43). (2) **audit_collide check 4, "text cut off"**: a line of words that a box
hiding its overflow (hidden / clip - not a scroll box) cuts part of; a line hidden whole is not judged. (3) **audit_deck
"strip"**: a cropped photograph (object-fit: cover, 160 px or wider) that shows under half of its height in a band, or under
40 % of its width in a column, fails - and `spilled_own` puts that slide's words in parts in the same build, which gives the
photograph its height. (4) **Every cropped photograph is framed on its subject** (`compile_module.photo_focus`): its record's
`"focus": [x, y]` (per cent), else the centre of its strong edges (Pillow; a ship's superstructure and hull, not the sky or
the ripples of the sea), written as `object-position` when it is 8 points or more off the middle - s11's ship came out at
41 / 65. (5) **A 3D model beside words takes at least 58 % of the width** (`SPLIT_3D` 0.42, whatever text share the sheet
asks; s26 had 50 % - 640 x 440 at 720 with nine names and six buttons over the model). (6) **kit3d in a small box** (under
720 x 460): the compact names and buttons (44 px), and a wide bar of buttons gets a band under the model (up to 34 % of the
height), never over it - the zones example filled 47 % of a 640 x 440 box and now 66 %. Still open: a builder may ask for
words in parts on a 3D slide whose script asks for the full screen; the audits do not judge how much of a 3D model the
names cover.

**The trainee's handout** (owner: *"only ONE button possible, thats handout ... if you are not opened any modules, handout
is big, with navigation, fast searching ... if module is opened, handout is about previous and this module"*). The
classroom's trainee page already had the one Handout button and finds `trainee/<module>/handout/index.html`; no factory step
wrote one. `compile/scripts/handout.py`, called by compile_course.py with the start pages: every approved module gets
`handout/index.html` - each slide's title and lines (the term before " - " in bold) and its photographs with their record and
credit, a task slide as its title; never the instructor's notes, a check's questions or a key - a contents list, a search
that keeps only the slides holding the words (and marks them), a photo that opens to full width. The classroom side (the
training app's join.js, staging): with a module open, the handout list is that module and the ones before it; with none
open, the whole course. Tests: test_run_audits 28, test_photo_focus 8, test_compile_module 467, test_compile_course 41,
test_course_package 79, test_precheck 39, test_kit3d, test_smoke3d 15, test_perf3d 13, test_review_sheets 18.

## 4zz18 · Lighter modules, lighter 3D, fewer hidden browsers (2.70.0, 2026-10-27)

The owner: *"optimize this course factory as much as can, put maybe better and lower size 3d models but quality, so it dont
lag ... so it does better work in smaller usage and less time"*. Measured before changing anything. (1) **The 3D scenes are
already light** - the seven example scenes have 5-25 k triangles and 35-85 draw calls (the catalogue of every part 49 k / 155);
a scene's spec is a few KB. What a tablet pays for is pixels: twice the screen's pixels, smoothed, full screen on a 2560 x 1600
tablet is 4 million a frame. **kit3d's pixel budget** (`PIXEL_BUDGET` 2.4e6, `P.size`): a slide's box keeps 2x, full screen is
drawn at 1.5x (still smoothed) - about half the graphics chip's work; 2.68.0's step-down on a slow tablet still applies on top.
(2) **Every module carried the kits' comments**: kit.js 379 KB and kit3d.js 158 KB per module (about 11 MB on a 20-module
course). `course-module-ui/scripts/minify_engines.py` makes `kit/min/kit.js` (221 KB) and `kit3d/min/kit3d.js` (88 KB) with
esbuild (the copy the Vercel command line brings, or NOVIKONTAS_ESBUILD); each copy's first line names its source's sha256 (line
ends as LF), and `design_system.shipped_src` ships the copy only while that matches - else the source, so an edit never ships an
old copy. The compile's "is the module's copy the factory's" checks (compile_module, task_pages) ask the same function;
`kit_parts.py promote` makes the copy again and names it in the git add. Globals and properties keep their names: the studio,
the audits and test_kit3d / test_studio / test_figure_fit (52) pass on the minified copies. (3) **The compile's drawing check
starts no browser for a page with nothing drawn on it** (`drawing_check.DRAWN`: no svg, img, canvas, video, object, iframe or
kit figure) - on gas M15 (2.67) the instructor's plan and the answer key took 48 s and 21 s, plus up to 80 s waiting for a
browser slot, and reported "drawings": 0. Measured but left: the figures stage's 330 s on that run was three modules building
at once (the first-build lock and the browser queue), not drawing - judged again on a quiet computer's timed build. Tests:
test_minify_engines 6, test_kit3d (+ the pixel budget), test_drawing_check (+ a plain page), test_compile_module 467.

## 4zz19 · Phase A with no agent, Phase B only for the pictures (2.73.0, 2026-10-28)

The owner's brief (2026-10-27, after the chem advanced run on 2.70.0): an average module in 10-15 min of AI time, builder
usage at least halved, simple modules to PASS with no agent - no law or check weakened, the visual review kept. The run:
21 modules, 18 builders at once hit the Workflow's 20-subagent cap, the CPU sat at 100 %, the browser slots and the cold-build
lock serialised the work (M11 46 min, M12 38, M17 117, M18 107, M10 96, M08 89); a local build refused to start on "the
starter's blanks - fill s07: its picture"; four scripts set scenes in a pump room the ship does not have; the gate passed on an
intake field. What changed:

1. **The picture slot in the script** (`content_script.py picture_of / picture_findings`): `"picture": {"kind":
   "photo|figure|3d|none", "aspect", "shows"}`; must-fix an unknown kind, one the visual does not need, no aspect, nothing to
   show; an older script is read from `visual_kind`. **The words a layout holds** are a must-fix at render (a line over a part's
   75 words); `parts_of` (the compiler's `auto_parts`) keeps the old cut when it fits, else the cut whose largest part is
   smallest (chem: 78-96-word parts on 9 slides). **Ship profile** (STANDARDS.md): a screen naming what the ship lacks is said.
2. **Phase A** - `--init-build` (after the colleague's 2.72.3 prefill) fills every empty slot with a placeholder
   (`compile/scripts/placeholder.py`: a grey PNG of the slot's shape at 1600 px, marked in the file, its record
   `rights_state: PLACEHOLDER`; a question's answers on a grid); `--fill-slots` for an older sheet. Placeholders are never a
   photo for L57, never an L58 duplicate. `build_module.py` grades the questions only (`review_sheets.mjs --grade-only`),
   measures each slot (`data-slot`, `run_audits --slots`), answers `PHASE A CLEAN` (exit 4) - never PASS - and a deck Phase A
   built is no "rebuild" until its first PASS (else new photographs under 800 px would pass as old ones; the M11 bench caught
   it). `check_course_package.py` refuses any placeholder. `phase_a.py <course> --modules 1-21`: one local queue
   (`browser_slots.count() // 3` at once), STILL RUNNING / --wait like a build.
3. **The needs file** `working_claude\visuals\MNN_VISUAL_NEEDS.md/.json` (`visual_needs.py`): per slot kind, shape, px at three
   sizes, words, what it must show, five catalogue candidates; the starter figures, the 3D scenes to place, the auto picks.
4. **The course photo catalogue** (`scripts/photo_catalogue.py index / assign / show`): every old-course picture with its
   slide's words, every knowledge-base picture with its caption or page text, the sourcing pass's finds; BM25 by what the slot
   must show, its title and words, plus the script's `from_old` slides; one pick per picture course-wide; `PHOTOS_TO_FIND.md`
   for ONE sourcing pass (`photos_found\`, `found_for`). Chem: 1,442 pictures in 10 s, 120 slots in 9 s; the builders' own
   choices were in the top 5 for 11 of 20 slots. **Only 1 of 120 slots is good enough for `--auto`** - most old-course pictures
   are under 800 px, which the pre-check rightly refuses: a simple module reaches PASS with no agent only once the sourcing
   pass has found its photographs.
5. **Starters**: a slide whose lines name no kit thing (a rule, a scenario, an order and its read-back) is a step track of its
   lines (`starter_track`, labels within 46 characters, never ending on a small word). figure_fit on chem M11/M17/M18: 16 of 32
   starters pass first time (2.70.0: 11 of 32, by the same measure without fixes 14 vs 11).
6. **Workflow** (`build_course.js`, on the colleague's 2.72.x shape): Phase A + the course photo pass before any builder; a
   module Phase A finished gets no builder (straight to the 3D step, the figure step and QA); a builder's brief is its needs
   file; one photo pass for the drafts. orchestration/GUIDE.md documents the 20-subagent cap and the browser slots.
7. **Gate**: only `kb_tool.py decision`'s record (with its date; yes / built: a folder that is a knowledge base) - never the
   intake field. `kb_tool.py find` also looks in `source_files\`.

Measured (bench copy of chem advanced, a quiet PC): Phase A M11 17 s, M17 38 s, M18 28 s (84 s for the three); Phase B on M11:
one Sonnet agent, PASS in 4.5 min, 120 k tokens, 38 tool calls, 4 builds (2.70.0's run: 46 min). Not measured yet: Phase B on
M17 / M18, a whole course. Not done: one agent serving several modules (the colleague's per-module judges and fix round keep
one builder per module). The owner decides whether Phase A / B becomes a law row.

## 4zz20 · L65 a drawing that moves stays smooth on the tablet (2.78.0, 2026-10-29)

Measured by the classroom session on a Lenovo Yoga Tab 11 (IGF M03 trainee deck): kit flows running in drawings whose
equipment cast CSS drop-shadows and whose lines were masked 8000 x 8000 kept the graphics chip 97 % busy - 32-43 fps,
65-100 ms hitches (its own layer: 38 -> 60 fps; no shadows: 33 -> 43). What changed, the look kept:

1. **`course-visuals/kit/kit.js`** - in a figure where anything moves for ever (`endless()`: running, infinite animations)
   each `.kit-m-drop` piece's shadow is **baked**: the piece written out as a stand-alone SVG (its computed styles, the
   gradients, patterns and clips it uses; what moves for ever left out), drawn on a canvas as its shadow alone, and put
   in as a PNG `<image>` under the piece (`g[data-kit-shade]`, never a shape to the layout or the drawing audit); the live
   filter off (`.kit-baked`). Baked after layout, after a step settles and after a value set from outside; again only
   when the piece changed; a piece the playing step moves casts its live shadow until it settles. The figure gets
   `.kit-moving` (its own layer). **`h.front`**: a pipe's or hose's contents are masked only while the fluid front stands
   part-way, the mask sized to the line (no mask full, nothing drawn empty). A flow at 0 is paused. **`h.soft`**: fire
   smoke and glow, spill vapour, the gas cloud's drifting puffs (its group blur is gone) and the spark's glow are radial
   (or, for a long flat shape, linear) gradient fills that
   look as the blur did; the spark's halo is two soft strokes. `kit.css`: `.kit-moving{will-change:transform}`,
   `.kit-m-drop.kit-baked{filter:none}`.
2. **`course-module-ux/measure/scripts/audit_motion.js`** (`AuditMotion.all()` / `.page()`): every slide, and every step of
   every kit figure on it - a filter or a mask in or round a drawing that moves for ever is a FAIL (named with its
   element, the step and the value); no own layer and the `stroke-dashoffset` count are notes. Loaded by `run_audits.py`
   with the deck, collide and compose probes (`motion` line). `audit_drawing.js` skips the baked shadows.
3. **Tests**: `test_audit_motion.py` (fixture `measure/fixtures/motion_defects.html`: four bad drawings found, two good ones
   silent, a kit figure passing at every step and failing with its bake undone; the kit's gallery passes its own rule).
   `test_run_audits.py` knows the fourth probe.
4. **Hit list** (`_claude/L65_HIT_LIST_2026-10-29.md`, on copies): IGF advanced as built - 130 hits in 19 of 30 modules
   (61 equipment shadows, 56 pipe masks, 8 gas-cloud blurs, 5 smoke / vapour / glow blurs); with the 2.78.0 kit - 0.
   GAS BASIC (hand-built) - 0. A rebuild of IGF on 2.78.0 clears it.

## 4zz21 · Every IGF Advanced build failure put right in the factory (2.80.0, 2026-10-29)

Aleksis: "fix all the failures" - the rebuild of six IGF Advanced modules on 2.79.0 failed on these, each now a factory fix:
1. **L65 in a real deck run.** The motion audit runs after three other probes in the same page; they leave a figure at a
   moving step while its slide is hidden, and showing the slide again by its class told the kit nothing - M03 s02, M06 s05
   kept live drop-shadows. `KIT.bake(scope)` bakes the figures of a slide just shown and `audit_motion.js` calls it, as the
   deck's own showing would; the kit also bakes on an animation's start and when the drawing comes into view, marks a
   drawing `data-kit-baking` from the moment a bake is due, and turns the live filter off when a bake starts (a slow or
   failed picture leaves no shadow, never the filter). A fluid front's mask (`data-kit-front`, sized to its line - L65
   allows it) is no longer a hit (M06 a01 step 2).
2. **Handouts** (`handout.py`): every handout had no way back (check_navigation FAIL, the learner trapped) and its own
   picture viewer instead of gb_zoom (course package, L51). Now the back link with history-back and gb_zoom.js / .css,
   as the deck and the task pages. `test_compile_course.py` +3.
3. **3D label pills** (`audit_deck.js`): a pill's 44 px hit box is its `::before`; the tap-target check measured only the
   26 px pill (M07 s01, three builds unchanged). It counts an absolute `::before` / `::after` that takes the tap.
   `test_audit_deck.py` +1, fixture `deck_tap_hitbox.html`.
4. **A task page the compiler builds no more** is removed unless a person changed it (M30's `tasks/fa1_variant_a.html`
   beside `assessment/final_a.html`, opened by no slide). `test_compile_module.py` C2b.
5. **`--module final`** is the folder that already holds the final (IGF Advanced: module30); counting the planned
   modules made a second final in module31. C2c.
6. **Words dressed as a drawing** (Aleksis, on M03 s08: "this doesn't move or do anything, just only shows text"): the
   grid starter put parts guessed from the slide's description (an engine, a gauge, a scale) beside captions no step
   ever moved, and those parts kept it from the step track a list of words gets. It adds none now when the lines name
   nothing the kit draws (`test_starter_figures.py` +1). `kit_meaning.py` STILL (a BLOCK): steps that only bring in
   free words beside machines or instruments that never move; a figure of nothing but words; a gauge, level or scale no
   step moves and nothing sets. On IGF Advanced: M01 s14, M03 s08, M08 s09, M12 s07 (and M18 s02, words only) -
   redrawn so every step moves what it names.
7. **`debrief_map.py`** crashed on `--module final` (`int('final')`): the final's paths are FINAL.json and its folder.
   `test_debrief_map.py` +1.
8. **3D labels built ahead** (`kit3d.js`): the slide before builds the next scene, its labels in a hidden layer but
   unplaced at (0, 0) - a probe that shows the slide by its class measured six pills on one spot (M05 s02). A label is
   `k3-off` until a frame places it. `test_kit3d.py` +1.
9. **The 3D full-screen button** (`gb_deck.js`) is placed for every 3D box on screen, not only the deck's current slide:
   shown by a class it stayed in its corner over the scene's "Labels" (M14 s04).
10. **`gb_interact.css`** (2.74.0) said "every colour a token" and held 38 raw colours: the factory's own strict look check
   failed a freshly set-up module. Now `--gi-*` tokens in its `:root` (the same values) and `--blue` / `--txt-d`.
   `references/vocabulary.md` names `gb_interact.js` + `.css` (two failures of `test_design_system.py`, on main too).
11. **"makes 2 separate 3D renderers"** (`check_course_package.py`) counted renderer code over the whole module: every
   module with a 3D slide and an interactive task was noted, though the deck's `kit3d.js` and a task page's
   `gb_interact.js` are never on one page. Now per page - the scripts a page loads. `test_course_package.py` +1.
12. **Builds side by side** (`check_course_package.py`): the classroom's importer read another module's audit page
   (`_audit_<pid>_WxH.html`, beside its deck while its checks run) as it was removed - "ENOENT", the package failed.
   A build's working files (TRANSIENT) are left out of the importer's copy and of the checks. `test_course_package.py` +1.
13. **A label box placed by hand** (`task_pages.py`): the compiler laid its own boxes in the label rows without knowing
   the hand-placed ones (IGF Advanced M06 q06: "insulation" over "hold space", found only by the leader-crossing review).
   `hand_box_overlaps` says it at compile, with the way out: place both, or neither. `test_task_engine.py` +1.
14. **A `tree` with many children** (`kit.js`): three spacings tried, then the row was drawn wider than the figure and the
   frame zoomed out - IGF Advanced M16 s03's five who receive a leak report were 10.5 px at 1024 x 768. With no
   grandchildren they now go to two rows, the second's boxes under the gaps of the first. `test_studio.py` +1 (fails on
   the old kit: the row reached 605 of 400 units). Also `test_studio.py`'s gas-cloud check looked for the blur filter
   L65 replaced (`g[filter]`): it crashed on main; it reads the cloud's growing group now.

## 4zz22 · Never a box for a thing - the kit makes the part (2.81.0, 2026-10-30)

The owner, on IGF Advanced M04 after 2.80.0: *"why didnt you create for other modules the unique kits???"*, *"also the
elements here are behind the pipes"*, *"remember this in the factory, dont just write these boxes MAKE THE KITS ASWELL"*.
1. **BOX by what a box does, not by its name** (`kit_meaning.py`): the 2.77.0 check knew a list of machine names, and a
   flame drawn inside a box let a "combustion chamber" pass. Now a solid `space` a pipe or hose runs into fails whatever
   its name (M04: combustion chamber, seawater scrubber, adsorption dryer, vessels A and B, expansion tank, membrane
   module; M09 / M12 / M17 suppliers; M20 calibration cradle). `test_meaning.py` +2.
2. **Pipes behind equipment** (`kit.js` `layer()`): parts were drawn in the spec's order, so a pipe listed after a dryer
   ran over it. Rooms and zones at the back, then lines, then equipment and words. `test_studio.py` +1.
3. **L55 (4)** in `docs/FACTORY_LAWS.md` and the builder card: never a box for a thing - the part the kit lacks is made.
4. **Eleven parts made and used** (course-visuals kit, promoted from the IGF Advanced build): `vessel` (kind plain,
   adsorber, scrubber, expansion, membrane), `burner` (an inert gas generator's chamber), `gas_monitor` (a portable
   multi-gas detector, its channels live, in its calibration cradle or seen from above), `flange_joint` (plain,
   insulating, bad), `hose_saddle`, `road_tanker`, `gangway`, `ramp`, `vehicle_queue`, `gantry`, `workstation`;
   figure-truths.json names them (equipment). 21 IGF Advanced figures redrawn with them (M04 x8, M09, M12 x3, M14, M17,
   M20 x3, M22, M23 x3, M27 x2). CATALOGUE.md's budget 15 -> 18 KB (a part a builder cannot find is drawn as a box).
Course findings put right in the build sheets: M03 s02 picture-left (L62), M14 s01 a photo cropped to the trucks and the
vessel (a panorama a column cut to the terminal between them), M05 s01 a library photo shown nowhere else (L58), M14 m02 /
s03 steps that move, M14 s03 picture-left (L62).

## 4zz23 · L66 every item a simulator can train is trained on one (2.82.0, 2026-10-30)

Course director Aigars Klūga, 2026-10-30 (team chat, in Latvian): the advanced courses use the school's physical
simulators for their practical tasks to the maximum - find which model-course competences they can cover and cover them
all; a simulator task may be on paper, the instructor grading from the instructor sheet. On IGF Advanced the map and
five draft tasks were made by hand the same day; this makes it a step of every advanced course.
1. **The lane** `coverage/SIMULATORS.md`: SIM_MAP.md from the manuals (every fact with its page), SIM_COVERAGE.json /
   .md - every leaf syllabus item COVERED / PARTLY / GAP / NOT-SIM - every GAP in a proposed task with the minutes'
   source inside its module, every such task drafted as an exercise (Trainee + Instructor form) in
   `to_review\exercises\sim_drafts\MNN\`, the decisions in the one Stage 2 pop-up. ILOs and hours unchanged.
2. **The school's simulators** `coverage/knowledge/simulators.json`: twelve models with their manuals (file, pages, page
   rule) on `G:\My Drive\Gas Library\documents\manual\` and the 2026-10-23 staging copy; which advanced course trains on
   which (IGF: LNG, MeOH, ERS; Gas: LPG, LNG membrane / spherical / regas, DFDE, steam LNGC, MPRI models; Oil: LCC); no
   chemical tanker manual was found - asked of the course director. Installation and options are asked, never assumed.
3. **The schema and the check** `coverage/knowledge/sim_coverage.schema.json`, `coverage/scripts/sim_coverage.py needed
   | init | check`: one row per leaf item (a line that only introduces children is not one), a page for every verdict on a
   simulator, the counts recounted, every GAP in a task, every GAP task's two forms present, minutes with their source.
   `test_sim_coverage.py` 23. On the hand-made IGF Advanced map it reports what is still open there: P1-P3 and P5 not
   linked to their drafts (29.1, 27.2, 8.2, 11.3), the injects P7, P8, P11 not drafted, GAP 3.3.5.a in no task.
4. **The step**: build order 4c (before the GATE; blocked without the syllabus and the old course), SKILL.md's gate
   section and L66 row, orchestration Rule 1 (simulator tasks settled before the fan-out; one agent per manual, then per
   competences, then per draft), `course_gate.py` says an incomplete map on every module start and never stops on it.

## 4zz24 · Every build carries its ILO map for the admin panel (2.83.0, 2026-10-30)

Aigars asked for an ILO map per course in the admin panel (every intended learning outcome, where it is taught, where it is
checked). The training app reads `instructor/_course_shell/ilo_coverage.json` from the published package; until now a node
tool in the training app (`tools/ilo-coverage.mjs`) made it by hand. The factory now makes it.
1. **`scripts/ilo_coverage.py <course> [out]`** - a port of that tool, the same format (`kind: "ilo-coverage"`, `version: 1`,
   course, built, approved, final_rule, main, modules, rows with taught slides, checked sets, practical exercises, a final
   count, `whole` / `exam` flags). Read off `working_claude/ilo_map.json`, `architecture.json`, `assessment_map.json` and
   `script/M*.json` + `FINAL.json`; nothing typed. Prints what is taught or checked nowhere and any tag no row owns.
   Checked against the node tool on the IGF Advanced and the IGF Basic courses: byte-identical output.
2. **Wired** into `compile/scripts/compile_course.py` (the step that finishes the modules folder, build order 15, run in the
   Cross-check assembly of `build_course.js` and by the publisher's compile): it writes
   `modules/_course_shell/ilo_coverage.json` on every build, rewritten each time; a course with no ILO map gets a line,
   never a stop.
3. **The publisher** (`course-tablet-publisher/knowledge/platform.json` `ships_in_course_shell_globs`, `gates.py classify`):
   the file ships with the course, sorted INSTRUCTOR before any internal glob is tried - never internal, never a trainee file.
4. **Proof:** `scripts/test_ilo_coverage.py` (18), two new checks in `test_compile_course.py`, three in `test_publisher.py`.

## 5 · Known gaps / before this goes live

Rewritten 2026-10-19 at 2.49.6. The list of 2026-09-10 said the factory had never driven a real course: it has since.
The IGF course (MC 7.13) was built from its approved scripts - M01-M15 and the final assessment, 2026-10-15 to
10-19 - and what each build found came back through the course's `working_claude/factory-notes.md` and build notes
and was fixed (§4zs-§4zx). What is still open:

**Waiting on the owner's decision** (also in PR #1)

1. **The hand-off screen.** The ruling of 2026-09-03 (`floor.json`) puts a hand-off screen after the module check,
   but the script allows no screen after the check, so every compiled deck ends on it and `check_static.py`
   reports 2 findings per module. Open question: should the compiler add the hand-off screen itself (it is not
   content)?
2. **Theory / practice balance on compiled decks.** From 2.52.0 the compiler writes `data-active` on every block, as
   the script's L49 split counts it: an active slide, a task slide and a room activity are all their minutes active, a
   plain theory slide 0 - so `check_balance.py` now runs on every compiled deck. Still open: an active slide of more
   than 10 minutes is a "100 % active theory block", which `check_balance` fails as a rename (no IGF M01/M02 slide is
   that long). Whether L49's count or check_balance's rule wins is the owner's call.
3. **Per-question Retry** (C16) stays out: it contradicts course-task-ux §9a (one opening, one result).

**Not built yet, on purpose**

4. **The script editor** - an instructor changing a script without an AI session. Its own proposal, later.
5. **Tap-to-open cards** built from the course's own material: automatic cards would hide the lines a stepping
   figure lights (L53); they wait for the script rewrite Aigars asked for (claim titles, one lead line).
6. **Latvian and Russian wording** has not had a native speaker's check.
7. **Real tablets.** Every measurement is in headless Chrome (1280x800, 1920x1080, 1024x768); the decks and task
   pages have not been run on the Training / Trainer terminals (L39 - the owner's).

**Checks weaker than they look**

8. **The count-claim check is advisory** (`verify_course.py`): a range sentence ("over two screens") reads like a size
   claim, and it still prints 3 on a correct course. A per-course declared pattern would fix it.
9. **`knowledge/build-order.json` names owners but enforces nothing.** The gate at step 5 is the only hard stop.
10. **Stated in 2.49.4 and not changed:** the nano-banana spending cap prices every picture and clip flat (EUR 0.10 /
    1.50, settable); `gemini_take.py take` moves the newest download without a name filter; the gate report is not
    tied to the staged content; secrets are scanned in text extensions only.

**Not measured**

11. **No cost pass on course-factory.** `novikontas-token-economics` was run on course-module-ux and course-task-ux
    (2026-09-03), not on this skill: its description length and worst-case single-lane load are unmeasured.

**The reference course** (GAS BASIC is not on the machine this list was rewritten on - as last recorded, 2026-09-10)

12. **GAS BASIC is 535 min over**, so `check_hours.py` exits 1 on it by design; moving the excess to the handout, per the
    owner's ruling, is course work, not a factory defect. **Its modules 1 and 8 had no module plan** - since 2.47.0
    `module_plan.py` builds the plan from the script, so compiling them would close it.
