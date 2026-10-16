# course-factory — MANIFEST

**v1 (2026-09-07) · Maintained by Raivis · part of the `course-factory` plugin, shared with colleagues through the marketplace**

Maintainer file. **Not read at runtime.** It exists so a session six months from now can pick
this up cold, including one with no memory of why any of it is the way it is.

---

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
  `search` then leaves the old edition out. Packs go to `<course>/_factory/retrieval/`, **never into the
  knowledge base**.
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

## 5 · Known gaps / before this goes live

1. **No real run yet.** Every script has been executed against GAS BASIC, but the skill has never
   driven a course from a brief. `templates/factory-notes.md` §9 is the channel for what that
   teaches; there is no companion file yet, so nothing has come back.
2. **The count-claim check is advisory, not solved.** Deck-size phrasing varies per course and a
   range sentence ("over two screens") reads like a size claim. It printed 13 wrong claims before
   narrowing and still prints 3 on a correct course. A per-course declared pattern would fix it.
3. **`build-order.json` names owners but enforces nothing.** Nothing stops a step running before
   its predecessor. The gate at step 5 is the only hard stop.
4. **GAS BASIC itself is not yet compliant.** It is 535 min over, so `check_hours.py` exits 1 on
   it by design. Rebalancing it — moving the excess to the handout, per the owner's ruling — is
   outstanding work, not a skill defect.
5. **No cost pass.** `novikontas-token-economics` has not been run against this bundle. The
   router is ~1.4k words and each lane is read alone, which is the intended shape, but the
   description length and worst-case single-mode load are unmeasured.
6. **Modules 1 and 8 of GAS BASIC have no module plan**, so the "one plan per module" rule this
   skill mandates is not yet true of the course it was derived from.
