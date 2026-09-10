# course-factory — MANIFEST

**v1 (2026-09-07) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Maintainer file. **Not read at runtime.** It exists so a session six months from now can pick
this up cold, including one with no memory of why any of it is the way it is.

---

## 1 · Design principles

- **This skill is a router and a law, not a builder.** It owns order, the hours law, ILO
  immutability, the ratio rule and the terminal contract. It writes no screens and no tasks —
  `course-module-ux` and `course-task-ux` do that, and they existed first.
- **Every rule in here is here because breaking it cost real rework on GAS BASIC.** Nothing is
  aspirational. Where a rule has a story, the story is in the file, because a rule nobody can
  trace is a rule nobody follows.
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
├── SKILL.md                              router: mode, brief, the four laws, gate, build order
├── MANIFEST.md                           this file
├── knowledge/
│   ├── build-order.json                  the 15 ordered steps + who owns each (authority)
│   └── delivery-contract.json            paths, flavours, course pack, git, offline (authority)
├── templates/
│   ├── COURSE_BRIEF.md                   what the operator types
│   └── factory-notes.md                  companion file, written by the skill during the run
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
| Owner wants 80/20 practical; the accredited programme allocates 19 % and the split is fixed by its own table | 80/20 is the target; where the programme forbids it the theory hours are **delivered as active learning**, and a theory block with no trainee activity is a defect. Owner's own fallback, made mandatory. |
| `novikontas-course-plan` owns "theory/practice ratio"; this skill also rules on ratio | Boundary: that skill **designs** the plan and states the ratio; this skill **enforces** the accredited arithmetic and owns the active-learning fallback. Named in the router's boundary table. |
| IMO model course vs approved programme | The programme governs. The model course is guidance, cited as support, never as authority. |
| `COURSE_START.json` has no hours field, but is owned elsewhere | Additive `hours` block only. The existing schema is never altered. Shape in `hours-rules.json`. |
| Memory said "exactly one `.slide-body` per section" | Wrong as a universal: photo, launch and check screens use other body classes. Corrected to **at most one**; two is the destructive bug. |

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
