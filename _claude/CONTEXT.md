# Working context — NOVIKONTAS Course Factory

For the next Claude session. Read this before touching anything in this repository.

**Status 2026-09-30: `course-factory` 2.11.2 + `nano-banana` 1.1.2. Phase 5 in progress.**
Phase 5 upgrades the factory to the owner's six-stage production process (intake → architecture
STOP → word-for-word content script STOP → pilot Module 1 with five roles → remaining modules →
final assessment and handover). The owner's decision record, the gap analysis and the approved
step plan are in **`docs/PHASE5_GAP_REPORT.md`** — read it before changing anything. Where the
owner's Phase 5 decisions conflict with an older rule, the Phase 5 decision wins and is recorded
in the owning skill and in `docs/FACTORY_LAWS.md`.

Approved order: step 0 (clean-up, **done in 2.10.1**) → step 11 (lighter loading, **done in
2.11.0**) → step 11b (style files copied, not read, **done in 2.11.1**) → step 11c (the factory's own style
files pass the strict look check, **done in 2.11.2**) → steps 1–5 →
STOP for the pilot course → Stages 1–3 on it → steps 6–10 → build the pilot Module 1. After every
step: stop, give the owner a short plain summary and the exact commit/push commands.

`claude plugin validate --strict` passes for both plugins and the marketplace; 6 test files,
139 tests, all passing at 2.10.0.

Not built yet: `course-evidence`, the `evidence-retriever` agent, the deterministic hooks,
`resources/engines/`.

### How it got here

| Version | Date | What |
|---|---|---|
| 2.0.0 | 2026-09-10 | Phase 2 — five proven skills migrated from `course-factory` 1.3.0 |
| 2.1.0 | 2026-09-10 | Phase 3 — `course-visuals`, `visual-sourcer`, the asset pipeline |
| 2.2 | 2026-09-11 | Phase 4B — repairs from the ETPB3 pilot |
| 2.3 | 2026-09-11 | Phase 4C — the composition system (`gb_compose.css`, L17) |
| 2.4 | 2026-09-11 | RETROFIT as a first-class mode (L18) |
| 2.5 | 2026-09-11 | figures proven alive (L20), task-page states |
| 2.6 | 2026-09-14 | PREVIEW → APPROVAL → PUBLISH (L21) |
| 2.7 | 2026-09-15 | a slide is not an internal document (L22) |
| 2.8 | 2026-09-15 | the picture comes first (L23); parallel module build |
| 2.9 | 2026-09-15 | a call and a folder; expert edits (L24); plain-language reports (L25) |
| 2.10 | 2026-09-29 | the `nano-banana` plugin as a dependency |
| 2.10.1 | 2026-09-30 | Phase 5 step 0 — stale pointers fixed, one law numbering |
| 2.11.0 | 2026-09-30 | Phase 5 step 11 — the long reasoning in `course-factory` and `course-task-ux` moved (word for word) into `references/`; new detail goes into lanes, never back into a SKILL.md |
| 2.11.1 | 2026-09-30 | Phase 5 step 11b — `course-module-ui/scripts/design_system.py` copies the style files and engines into a module and proves them identical; the model reads `references/vocabulary.md` instead of ~58 KB of CSS |
| 2.11.2 | 2026-09-30 | Phase 5 step 11c — 128 raw colours in four shared style files became file-local named tokens with identical values; the strict look check passes on the factory's own files; look proven unchanged (computed styles and screenshots) |

---

## Install, and where it lands

```
claude plugin marketplace add silkansraivis3-tech/factory-mjaso
claude plugin install course-factory@novikontas-course-factory
```

| | |
|---|---|
| CLI | 2.1.267, native install at `%USERPROFILE%\.local\bin\claude.exe` |
| Plugin | `course-factory` **2.10.x** + `nano-banana` 1.1.x @ `novikontas-course-factory`, scope user |
| Installed cache | `~/.claude/plugins/cache/novikontas-course-factory/course-factory/<version>/` |
| Colleague instructions | `docs/INSTALL_FOR_COLLEAGUES.md` (authoritative copy) |

**Do not confuse the two binaries.** `%LOCALAPPDATA%\AnthropicClaude\claude.exe` is the desktop app
and has no `plugin` subcommands. The CLI is the one under `.local\bin`.

**Edit the repository, not the installed cache** — the cache is overwritten on update. After a
change: **bump `plugin.json`'s `version`** (Claude Code pins a git plugin to its version string and
will not update without it), push, then `claude plugin marketplace update` and `claude plugin update`.

---

## The six skills

| Skill | Owns |
|---|---|
| `course-factory` | programme, hours law, ILO immutability, build order, coverage, the gate |
| `course-module-ux` | how the delivery works — one page, Start, Next, the screen floor, the run script |
| `course-module-ui` | how a page **looks like a NOVIKONTAS page** — tokens, type, components |
| **`course-visuals`** | **what representation teaches a concept**, and where the asset comes from |
| `course-task-ux` | how a trainee answers or completes |
| `course-tablet-publisher` | publishing to the two terminals and the shared repository |

Agents: **`visual-sourcer`** — isolated-context asset investigation only; **`nano-banana:image-director`**
— generates realistic pictures and short clips. Picture generation goes to `image-director`, never to
a model override (until 2.10.1 four files said `Agent(model: "fable")`, which cannot make a picture).

**Second plugin, `nano-banana`** (`./nano-banana`, 1.0.0, 2026-09-29) — a stdlib-Python MCP server
for Gemini image (Nano Banana) and Veo video generation, the `realistic-visuals` skill and the
`image-director` agent. `course-factory` 2.10.0 declares it as a **dependency**, so it installs with
the factory. It is level 4 *generated illustration* of the `course-visuals` pipeline, never a
replacement for an authored schematic. One shared Gemini key. There is no `userConfig`: on first
use without a key, the server opens a tkinter window (PowerShell/osascript fallback), the user
pastes the key, it is checked, and it is saved to `~/.config/nano-banana/gemini_api_key`. The key
never passes through the chat. **Never commit a key to this public repo.**

The boundary that gets blurred: `course-module-ui` owns the **card as a component**. Using cards as
the *answer to a teaching need* is `course-visuals` failing to name the need. Neither restates the
other, and `course-visuals` deliberately contains no colour, radius, contrast or tap-size rule.

---

## Locations

| | | |
|---|---|---|
| Reference course | `C:\Users\raiviss\Desktop\docling\gas_basic\GAS Basic` | **READ ONLY** |
| Android application | `C:\Users\raiviss\AndroidStudioProjects\NOVIKONTASTraining` | **READ ONLY** |
| Old skill bundle | `C:\Users\raiviss\Desktop\novikontas-course-skills` → `github.com/silkansraivis3-tech/course-factory` | superseded; **read-only, do not delete or archive** (D-1) |
| Legacy skills backup | `Desktop\factory-work\_legacy_personal_skills_backup_2026-09-10` | the removed v1.3.0 personal copies |
| Colleague handover | `Desktop\course-factory-handover` | **repointed at the marketplace in Phase 3**; old scripts retired into `_superseded_2026-09-10/` |
| This repository | `github.com/silkansraivis3-tech/factory-mjaso` | **the only write target** |

The Phase 1 brief gave the reference course path as `docling\gas\_basic\GAS Basic`; the real path is
`docling\gas_basic\GAS Basic`. `Desktop\gas basic` is an older, superseded root — **not** it.

---

## Owner decisions

| | |
|---|---|
| **D-1 · VERIFIED** | `factory-mjaso` supersedes `course-factory`; parity and installation both proven. The old repository is untouched. |
| **D-3 · RESOLVED** | Organisation `novikontas-*` skills are **not** copied in. Use the org skill when installed, otherwise the fallback in `plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`, and record the route in `factory-notes.md` §0. |
| **D-2, D-4, D-5, D-6** | Still open — `docs/COURSE_FACTORY_BLUEPRINT.md` §9. |

---

## Findings

**F-1 · RESOLVED.** `plugin/CLAUDE.md` removed; the laws are now `docs/FACTORY_LAWS.md`, marked as
documentation, each naming its enforcing skill. L12 and L13 gained `course-visuals`. **All
twenty-five laws have an enforcing skill** (L1–L25; `course-factory/SKILL.md` uses the same
L-numbers since 2.10.1). `--strict` passes clean.

**F-2 · STILL OPEN.** `course-module-ux/build/GUIDE.md` §8 and `MANIFEST.md` line 158 say the record
engines live in `gas-basic-module-ux/assets/` "as the only copies". That skill is gone.
Pre-existing; closing it is the `resources/engines/` job.

**F-3 · CLOSED** in Phase 2B — duplicate personal skills removed.

**F-4 · RESOLVED.** The handover installer is retired and repointed at the marketplace; the
authoritative instructions are `docs/INSTALL_FOR_COLLEAGUES.md`.

---

## Rules in force

- The reference course, `source_files/`, the knowledge base, the Android application and the old
  `course-factory` repository are **read-only**. This repository is the only place to write.
- **Migration fidelity outranks tidiness** for the five migrated skills — their rules came from real
  production failures. Do not simplify or reword one; if something must change, make the smallest
  change and document it.
- Never bring the ICS/SIGTTO figures here — six are marked *NOT cleared for issue or publication*.
- Do not duplicate organisation-skill content into the plugin (D-3).
- Do not restore installation into `~/.claude/skills/`.
- The owner commits, publishes and installs. The factory builds and reports.

---

## What has and has not been proved

**Proved, on synthetic fixtures (Phase 3 onward):** the asset hierarchy, provenance and rights
escalation, animation rejection, the figure-alive probe, routing, expert-edit detection, the
slide-text and plain-language checks, the publisher gates — the six test files.

**Proved on real material:** retrofit pilots of ETPB3 / ETPA4 modules (Phases 4B–4C).

**Not proved:** a new course built end to end from a knowledge base. The Phase 5 pilot is that test.
`check_visuals.py` reads only **static** markup — a figure built by JavaScript at runtime is
invisible to it, which is why the human review in `course-visuals/review/GUIDE.md` is not optional.

---

## Next session

Continue the Phase 5 step plan in `docs/PHASE5_GAP_REPORT.md` §4, in the owner's approved order
(above). The owner's answers to Q1–Q5 and the approved order are in that report's **§6** — they
override the §4 proposals where they differ.
