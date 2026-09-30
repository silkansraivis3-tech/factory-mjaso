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
