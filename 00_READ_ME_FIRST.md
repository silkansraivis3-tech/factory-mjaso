# NOVIKONTAS Course Factory — read me first

**Phase 1: architecture only. Nothing is built yet.**

This repository holds the design for a reusable Course Factory — a Claude Code system that turns an
approved training programme, a set of source documents and a sentence from a colleague into a
finished course running on the company's Android tablets.

Phase 1 inspected the finished GAS BASIC course, the Android training application, the existing skill
bundle and the current Claude Code extensibility documentation, and extracted the reusable system
behind them. **No production skill, agent, hook or plugin has been created.**

---

## Read in this order

| | | |
|---|---|---|
| 1 | [`docs/COURSE_FACTORY_BLUEPRINT.md`](docs/COURSE_FACTORY_BLUEPRINT.md) | **Start here.** What to build in Phase 2, why each skill and agent exists, and the six decisions needed first. |
| 2 | [`docs/COURSE_PRODUCTION_PROCESS.md`](docs/COURSE_PRODUCTION_PROCESS.md) | How a course is actually made, gate to handover. |
| 3 | [`docs/GOLDEN_COURSE_EXTRACTION.md`](docs/GOLDEN_COURSE_EXTRACTION.md) | What GAS BASIC is, how it was produced, which parts are reusable and which are not. |
| 4 | [`docs/ANDROID_INTEGRATION_CONTRACT.md`](docs/ANDROID_INTEGRATION_CONTRACT.md) | What a generated course must satisfy to work inside the app. Read directly from the Kotlin, not from documentation. |
| 5 | [`docs/FACTORY_RULE_CLASSIFICATION.md`](docs/FACTORY_RULE_CLASSIFICATION.md) | Every rule sorted into law / skill / agent / hook / component / reference / Android / specific / discard, plus eight named contradictions. |
| — | [`_claude/CONTEXT.md`](_claude/CONTEXT.md) | Working context for the next Claude session. Read this before touching anything. |

---

## The three things worth knowing before you read any of it

**1 · The factory already exists, at about 70 %.**
`github.com/silkansraivis3-tech/course-factory` holds five working skills at v1.3.0, fifteen Python
scripts (eleven of them checks and gates), five in-page measurement probes, and a publisher with an
eight-check gate. They produced a 43-academic-hour accredited course running on two Android terminals
with zero dead links, zero dead ends, 64/64 programme topics and 266/266 IMO model-course outcomes.
Phase 2 is a migration plus four
additions, not a rewrite. Those rules are the scar tissue of specific recorded failures and should
not be re-derived from scratch.

**2 · The four holes are real, and one of them is the reason this project was started.**
There is no owner for **instructional visuals** — which representation a concept should take, and what
makes an animation teach rather than decorate. There is no owner for the **asset pipeline** —
sourcing, licences, provenance, rights. There is no **general evidence retrieval** (the existing one is
GAS-BASIC-only). And there is **no deterministic protection** — every law currently depends on the
model remembering it.

**3 · One Android constraint changes what a course may contain, and it is not written down anywhere
else.** The app's WebView answers **403 to every host except the classroom backend**, only navigates
to `.html`, ignores `target="_blank"` and `window.open`, and drives the hardware Back button by
clicking an element the page must provide. The shipped course loads its brand typeface from Google
Fonts on roughly 105 pages — on the tablet that request is blocked by the app itself and the typeface
never loads. See [`docs/ANDROID_INTEGRATION_CONTRACT.md`](docs/ANDROID_INTEGRATION_CONTRACT.md) §3.

---

## What was inspected

- The GAS BASIC course tree — 8 modules, decks, tasks, handouts, assessments, instructor guides,
  assets, and the 185-file `_claude_working_area` (102 documents) of briefs, evidence, QA and tooling
- The delivered course inside the Android app — 295 files in the trainee terminal, 110 in the
  instructor terminal
- `MainActivity.kt` (601 lines) and `build.gradle.kts` — the real integration contract
- The existing five-skill bundle, its fifteen scripts and its in-page measurement probes
- Current official Claude Code documentation on plugins, marketplaces, skills, agents and hooks

**Read-only, and untouched:** the GAS BASIC course, `source_files/`, `knowledge_base/`, and the
Android application. This repository is the only write target.

---

## Recommended next phase

**Scaffold the plugin in this repository and migrate the five proven skills unchanged**, before
writing anything new. Validate with `claude plugin validate --strict`, install from the marketplace,
and confirm all surfaces load. Everything else in the blueprint depends on that container existing.

The six decisions in `COURSE_FACTORY_BLUEPRINT.md` §9 should be answered first — **D-1** (does this
repository supersede `course-factory`?) and **D-3** (the `novikontas-*` dependency) change the shape
of the work.
