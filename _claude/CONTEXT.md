# Working context — NOVIKONTAS Course Factory

For the next Claude session. Read this before touching anything in this repository.

**Status: Phase 3 complete, 2026-09-10. Plugin 2.1.0.** The instructional visual system is built:
`course-visuals`, the `visual-sourcer` agent, the four-level asset pipeline, three reusable visual
engines, and the visual quality gate. **F-1 and F-4 resolved.** `claude plugin validate --strict`
passes clean.

Not built yet, and deliberately so: `course-evidence`, the `evidence-retriever` and
`module-producer` agents, the deterministic hooks, `resources/engines/`.

---

## Install, and where it lands

```
claude plugin marketplace add silkansraivis3-tech/factory-mjaso
claude plugin install course-factory@novikontas-course-factory
```

| | |
|---|---|
| CLI | 2.1.267, native install at `%USERPROFILE%\.local\bin\claude.exe` |
| Plugin | `course-factory` **2.1.0** @ `novikontas-course-factory`, scope user |
| Installed cache | `~/.claude/plugins/cache/novikontas-course-factory/course-factory/2.1.0/` |
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

Agent: **`visual-sourcer`** — isolated-context asset investigation only.

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
documentation, each naming its enforcing skill. L12 and L13 gained `course-visuals`. **All sixteen
laws have an enforcing skill.** `--strict` passes clean.

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

## What Phase 3 proved, and what it did not

**Proved, on synthetic fixtures:** the asset hierarchy in all three states (project wins · factory
wins when project absent · `GENERATED_ASSET_REQUIRED` when nothing exists) · provenance validation
clean and broken · **rights escalation blocks** · **animation rejection** catches decorative motion,
missing reduced-motion guard, box-and-arrow chains, card grids, remote assets and tiny SVG labels ·
a well-built teaching animation passes clean · the shipped patterns pass their own checks · all 15
existing scripts still execute · `check_hours.py` and `audit_ui.py` unchanged in behaviour.

**Not proved: any of it against a real course.** Everything was synthetic. The first real module is
the test. `check_visuals.py` also reads only **static** markup — a figure built by JavaScript at
runtime is invisible to it, which is why the human review in `review/GUIDE.md` is not optional.

---

## Next session

**Build `course-evidence`** by generalising the project-local `gas-basic-kb-retrieval`: authority
tiers, the four-level escalation, the citation format, GREEN/YELLOW/RED, and the rule that a
`content.md` over about a megabyte is never read whole. `NO SOURCE = NO MARITIME CLAIM` is the
strongest rule in the system and still has no general owner.

Then the `evidence-retriever` agent, then the hooks, then `resources/engines/` (which closes F-2).

**Before any of that, if the owner is ready:** run one real module of a second course end to end.
The blueprint's step 9 is the acceptance test, and every phase so far has been validated on
fixtures rather than on a course.
