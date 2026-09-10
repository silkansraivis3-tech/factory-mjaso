# NOVIKONTAS Course Factory — read me first

**Phase 2 complete: the plugin exists and the five proven skills are migrated. Not yet installed.**

This repository is the Course Factory — a Claude Code plugin that turns an approved training
programme, a set of source documents and a sentence from a colleague into a finished course running
on the company's Android tablets.

Phase 1 extracted the architecture from the finished GAS BASIC course, the Android application and
the existing skill bundle. Phase 2 built the plugin container and migrated the five proven skills
from `course-factory` 1.3.0 (`4dc5ff9`) to `course-factory` **2.0.0** here — 64 of 66 files
byte-identical, the other two additively extended for decision D-3 and nothing else.

**Still to build:** `course-visuals`, `course-evidence`, the three agents, the hooks, and the shared
`resources/` inventory.

---

## Install

```
/plugin marketplace add silkansraivis3-tech/factory-mjaso
/plugin install course-factory@novikontas-course-factory
```

**Not yet verified** — the Claude Code CLI is not installable on the machine Phase 2 ran on, so the
install flow has never been executed. The acceptance checklist is in
[`docs/PHASE2_MIGRATION_REPORT.md`](docs/PHASE2_MIGRATION_REPORT.md) §7, and running it is the first
job of Phase 3.

---

## Read in this order

| | | |
|---|---|---|
| 1 | [`docs/PHASE2_MIGRATION_REPORT.md`](docs/PHASE2_MIGRATION_REPORT.md) | **Start here if you are continuing the work.** What was migrated, from which commit, what was validated, what could not be, and what blocks Phase 3. |
| 2 | [`docs/COURSE_FACTORY_BLUEPRINT.md`](docs/COURSE_FACTORY_BLUEPRINT.md) | The architecture: why each skill and agent exists, and the decisions still open. |
| 3 | [`docs/COURSE_PRODUCTION_PROCESS.md`](docs/COURSE_PRODUCTION_PROCESS.md) | How a course is actually made, gate to handover. |
| 4 | [`docs/GOLDEN_COURSE_EXTRACTION.md`](docs/GOLDEN_COURSE_EXTRACTION.md) | What GAS BASIC is, how it was produced, which parts are reusable and which are not. |
| 5 | [`docs/ANDROID_INTEGRATION_CONTRACT.md`](docs/ANDROID_INTEGRATION_CONTRACT.md) | What a generated course must satisfy to work inside the app. Read directly from the Kotlin, not from documentation. |
| 6 | [`docs/FACTORY_RULE_CLASSIFICATION.md`](docs/FACTORY_RULE_CLASSIFICATION.md) | Every rule sorted into law / skill / agent / hook / component / reference / Android / specific / discard, plus eight named contradictions. |
| — | [`plugin/CLAUDE.md`](plugin/CLAUDE.md) | The sixteen global laws, one line each, each naming the skill that enforces it. |
| — | [`_claude/CONTEXT.md`](_claude/CONTEXT.md) | Working context for the next Claude session. Read this before touching anything. |

---

## The three things worth knowing before you read any of it

**1 · The five migrated skills were not written for this repository — they were earned.**
They come from `course-factory` v1.3.0, built during GAS BASIC production: fifteen Python scripts
(eleven of them checks and gates), five in-page measurement probes, and a publisher with an
eight-check gate. They produced a 43-academic-hour accredited course running on two Android
terminals with zero dead links, zero dead ends, 64/64 programme topics and 266/266 IMO model-course
outcomes. Every rule in them is the scar tissue of a specific recorded failure. **Do not simplify,
reword or tidy one** — if it looks arbitrary, find out what it cost before touching it.

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

**Verify the installation**, in an interactive `claude` terminal, using the checklist in
`docs/PHASE2_MIGRATION_REPORT.md` §7. Decision **D-1** makes `factory-mjaso` authoritative only once
migration parity *and* installation both pass — parity is proven, installation is not. Until then
the old `course-factory` repository stays as it is: read-only, not archived, not modified.

Then build `course-visuals`. It is the largest genuine gap, it is the stated reason the factory
exists, and it is the first owner for laws **L12** and **L13**, which currently have none.

**D-1** and **D-3** are resolved. **D-2, D-4, D-5 and D-6** in `COURSE_FACTORY_BLUEPRINT.md` §9 are
still open.
