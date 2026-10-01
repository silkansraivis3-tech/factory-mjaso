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
├── scripts/old_course.py, test_workspace.py   the old course read whole, its pictures copied out (L41, 2.19.0)
├── knowledge/media-and-tasks.json        the kinds of picture and the ways of answering, who makes each, the variety floors (L37, L38, 2.18.0)
├── knowledge/page-labels.json            the review pages' own words in the operator's language (en / lv / ru)
├── script/GUIDE.md                       READ IN: Stage 3 - the content script (2.16.0)
├── scripts/content_script.py, check_script_match.py, test_content_script.py   the script, the Word copy, corrections on confirmation, the word-for-word match
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
claim (an operator's stated fact is a source), offline tablet.

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
