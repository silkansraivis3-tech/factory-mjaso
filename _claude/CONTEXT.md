# Working context — NOVIKONTAS Course Factory

For the next Claude session. Read this before touching anything in this repository.

**Status: Phase 2B complete, 2026-09-10.** The plugin is published, **installed from the GitHub
marketplace and verified** on Claude Code CLI 2.1.267. **D-1 is VERIFIED — `factory-mjaso` is the
authoritative Course Factory.** The superseded personal skills are gone.

Not built yet, and deliberately so: `course-visuals`, `course-evidence`, the three agents, the
hooks, the `resources/` inventory.

---

## Install, and where it lands

```
claude plugin marketplace add silkansraivis3-tech/factory-mjaso
claude plugin install course-factory@novikontas-course-factory
```

| | |
|---|---|
| CLI | 2.1.267, native install at `%USERPROFILE%\.local\bin\claude.exe` |
| Marketplace | `novikontas-course-factory` |
| Plugin | `course-factory` **2.0.0**, scope user, enabled |
| Installed cache | `~/.claude/plugins/cache/novikontas-course-factory/course-factory/2.0.0/` — 70 files |
| Always-on token cost | ~1,202 per session |

**Do not confuse the two binaries.** `%LOCALAPPDATA%\AnthropicClaude\claude.exe` is the desktop
app (1.49585.0) and has no `plugin` subcommands. The CLI is the one under `.local\bin`.

---

## What this repository is

```
.claude-plugin/marketplace.json          novikontas-course-factory
plugin/
  .claude-plugin/plugin.json             course-factory 2.0.0
  CLAUDE.md                              16 global laws (see F-1 - not auto-loaded)
  skills/                                the five migrated skills
    course-factory/                        + org/ORG_DEPENDENCIES.md (the D-3 fallback)
    course-module-ux/  course-module-ui/  course-task-ux/  course-tablet-publisher/
  resources/README.md                    empty by design in 2.0.0; Phase 3 fills it
docs/                                    Phase 1 architecture + PHASE2_MIGRATION_REPORT.md
_claude/CONTEXT.md                       this file
```

**Edit the repository, not the installed cache.** The cache is overwritten on update. After a
change: bump `plugin.json`'s `version` — Claude Code pins a git-sourced plugin to its version
string and will not update installed copies without it — then push, then
`claude plugin marketplace update novikontas-course-factory` and `claude plugin update`.

---

## Locations

| | | |
|---|---|---|
| Reference course | `C:\Users\raiviss\Desktop\docling\gas_basic\GAS Basic` | **READ ONLY** |
| Android application | `C:\Users\raiviss\AndroidStudioProjects\NOVIKONTASTraining` | **READ ONLY** |
| Old skill bundle | `C:\Users\raiviss\Desktop\novikontas-course-skills` → `github.com/silkansraivis3-tech/course-factory` | superseded; **read-only, do not delete or archive** (D-1) |
| Legacy skills backup | `C:\Users\raiviss\Desktop\factory-work\_legacy_personal_skills_backup_2026-09-10` | the removed v1.3.0 personal copies, 68 files |
| Old file-copy installer | `C:\Users\raiviss\Desktop\course-factory-handover` | **now misleading — see F-4** |
| This repository | `github.com/silkansraivis3-tech/factory-mjaso` | **the only write target** |

The Phase 1 brief gave the reference course path as `docling\gas\_basic\GAS Basic`; the real path is
`docling\gas_basic\GAS Basic`. `C:\Users\raiviss\Desktop\gas basic` is an older, superseded root —
**not** the reference course.

---

## Owner decisions

| | |
|---|---|
| **D-1 · VERIFIED** | `factory-mjaso` supersedes `course-factory`, and the switchover is complete — parity and installation both proven. The old repository is untouched. |
| **D-3 · RESOLVED** | Do **not** copy the `novikontas-*` organisation skills into the plugin. Use the org skill when installed, otherwise the minimal fallback in `plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`, and record the route in `factory-notes.md` §0. The organisation plugin is **not** created yet. |
| **D-2, D-4, D-5, D-6** | Still open — `docs/COURSE_FACTORY_BLUEPRINT.md` §9. |

---

## Findings carried into Phase 3

**F-1 · `plugin/CLAUDE.md` is not loaded — now confirmed by the official validator.**
`claude plugin validate` warns: *"CLAUDE.md at the plugin root is not loaded as project context. To
ship context with your plugin, use a skill instead."* It is the **only** warning, and the only
reason `--strict` fails. Non-strict passes. **L12** (asset provenance) and **L13** (animation must
explain a mechanism) still have **no enforcing skill** until `course-visuals` exists. Options in the
migration report §6.

**F-2 · Record-engine code points at a deleted skill.** `course-module-ux/build/GUIDE.md` §8 and
`MANIFEST.md` line 158 say the record engines live in `gas-basic-module-ux/assets/` "as the only
copies". That skill is superseded and gone. **Pre-existing, not introduced by migration** — left
unchanged on purpose. Candidate for `resources/engines/`.

**F-3 · CLOSED.** The duplicate personal skills were removed in Phase 2B. `~/.claude/skills/` is
empty and the only copies live in the plugin cache.

**F-4 · The old file-copy installer is now misleading.**
`Desktop/course-factory-handover/install.ps1` and `FOR-YOUR-COLLEAGUE.md` still install a
superseded v1.3.0 copy into `~/.claude/skills/`, a directory the plugin no longer uses — and the
doc omits `course-module-ui`, which the build order makes required (contradiction C-6). Retire it
or repoint it at the marketplace before another colleague follows it. Not done in Phase 2B, which
was documentation-only outside the plugin system.

---

## Rules in force

- The reference course, `source_files/`, the knowledge base, the Android application and the old
  `course-factory` repository are **read-only**. This repository is the only place to write.
- **Migration fidelity outranks tidiness.** The five skills' rules came from real production
  failures. Do not simplify, reword or "clean up" one. If something must change, make the smallest
  change and document it in the migration report.
- Never bring the ICS/SIGTTO figures here — six are marked *NOT cleared for issue or publication*.
- Do not duplicate organisation-skill content into the plugin (D-3).
- The owner commits, publishes and installs. The factory builds and reports.

---

## What Phase 2B proved

CLI 2.1.267 installed by the official native Windows method · `claude plugin validate` passes with
one warning (F-1) · marketplace added from GitHub · plugin installed at 2.0.0 **by the same path a
colleague uses**, not hand-copied · five skills enumerated by `claude plugin details` · 70 installed
files matching the repository · all 12 scripts execute from the installed cache · cross-skill
sibling resolution works there · `check_hours.py` and `verify_links.py` each produced a real PASS
and a real intentional FAIL · legacy duplicates backed up and removed · `claude doctor` clean ·
old repo, Android project and GAS BASIC all verified unmodified.

No course was created. No knowledge base was read. Fixtures were synthetic and deleted.

---

## Next session

**Build `course-visuals`** — the largest gap, the stated reason the factory exists, and the first
owner for L12 and L13. The blueprint's order (§10) puts it before `course-evidence`, the agents and
the hooks.

Deciding F-1 pairs naturally with it, since `course-visuals` is where L12 and L13 land anyway.
