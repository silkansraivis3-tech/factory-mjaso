# Working context — NOVIKONTAS Course Factory

For the next Claude session. Read this before touching anything in this repository.

**Status: Phase 2 complete, 2026-09-10.** The marketplace and plugin exist; the five proven skills
are migrated at plugin version **2.0.0** — 64 of 66 files byte-identical, two additively
extended for D-3. **The install flow has never been run** —
verifying it is the first job of Phase 3.

Not built yet, and deliberately so: `course-visuals`, `course-evidence`, the three agents, the
hooks, the `resources/` inventory.

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

---

## Locations

| | | |
|---|---|---|
| Reference course | `C:\Users\raiviss\Desktop\docling\gas_basic\GAS Basic` | **READ ONLY** |
| Android application | `C:\Users\raiviss\AndroidStudioProjects\NOVIKONTASTraining` | **READ ONLY** |
| Old skill bundle | `C:\Users\raiviss\Desktop\novikontas-course-skills` → `github.com/silkansraivis3-tech/course-factory` | **read-only migration source. Do not delete, archive or modify** (D-1) |
| Personal skills | `C:\Users\raiviss\.claude\skills\` — five `course-*` folders, frozen at 1.3.0 | see F-3 |
| Colleague handover | `C:\Users\raiviss\Desktop\course-factory-handover` | the old file-copy installer; superseded by the plugin |
| This repository | `github.com/silkansraivis3-tech/factory-mjaso` | **the only write target** |

The Phase 1 brief gave the reference course path as `docling\gas\_basic\GAS Basic`; the real path is
`docling\gas_basic\GAS Basic`. `C:\Users\raiviss\Desktop\gas basic` is an older, superseded root —
**not** the reference course.

---

## Owner decisions

| | |
|---|---|
| **D-1 · RESOLVED** | `factory-mjaso` supersedes `course-factory` — but **only after migration parity and installation validation both pass**. Parity is proven (64/66 byte-identical; 2 additive D-3 edits, 1 new file, nothing else). Installation is not. Until then the old repository is untouched and the switchover is incomplete. |
| **D-3 · RESOLVED** | Do **not** copy the `novikontas-*` organisation skills into the plugin. Use the org skill when installed, otherwise the minimal fallback in `plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`, and record the route in `factory-notes.md` §0. The organisation plugin is **not** created yet. |
| **D-2, D-4, D-5, D-6** | Still open — `docs/COURSE_FACTORY_BLUEPRINT.md` §9. |

---

## Findings carried into Phase 3

**F-1 · `plugin/CLAUDE.md` is not loaded by Claude Code.** The official reference states a
plugin-root `CLAUDE.md` is not loaded as project context. The file exists and says so at the top,
and each law names the skill that enforces it. **L12** (asset provenance) and **L13** (animation
must explain a mechanism) have **no enforcing skill** until `course-visuals` exists. Deciding how
the laws reach a session is a Phase 3 decision — three options in the migration report §6.

**F-2 · Record-engine code points at a deleted skill.** `course-module-ux/build/GUIDE.md` §8 and
`MANIFEST.md` line 158 say the record engines live in `gas-basic-module-ux/assets/` "as the only
copies". That skill is superseded and gone. **Pre-existing, not introduced by migration** — left
unchanged on purpose. Candidate for `resources/engines/`.

**F-3 · Two copies of every skill will coexist.** The five folders in `~/.claude/skills/` are plain
personal skills; plugin skills are namespaced and the documentation says both remain available. One
copy frozen at 1.3.0 is a drift source. Removing the personal copies is part of confirming the
switchover, and it is the owner's action.

---

## Rules in force

- The reference course, `source_files/`, the knowledge base, the Android application and the old
  `course-factory` repository are **read-only**. This repository is the only place to write.
- **Migration fidelity outranks tidiness.** The five skills' rules came from real production
  failures. Do not simplify, reword or "clean up" one. If plugin packaging forces a change, make the
  smallest one and document it in the migration report.
- Never bring the ICS/SIGTTO figures here — six are marked *NOT cleared for issue or publication*.
- Do not duplicate organisation-skill content into the plugin (D-3).
- The owner commits, publishes and installs. The factory builds and reports.

---

## What was verified in Phase 2, and what was not

**Verified:** git-blob parity against the source at `4dc5ff9` — 64 of 66 blobs identical, 2
additively extended, 1 added, which is exactly the three D-3 changes and nothing else · marketplace and plugin manifests against the
current documented schema (22 checks, 0 failures) · all five skills discoverable with valid
frontmatter · every script imports and parses args from the plugin location · cross-skill sibling
resolution works (`publish.py` → `course-factory`) · `audit_ui.py` loads its sibling tokens ·
`verify_links.py` catches a planted dead link · `check_hours.py` passes an exact plan and fails a
+40-minute one with the right message.

**Not verified:** `claude plugin validate --strict` and the marketplace install. The CLI is not
installed on this machine and the only `claude.exe` present is the desktop app, which has no
`plugin` subcommands. Nothing was faked and no Claude configuration was edited.

No course content or knowledge base was read in Phase 2, as instructed.

---

## Next session

1. Run the acceptance checklist in `docs/PHASE2_MIGRATION_REPORT.md` §7 in an interactive `claude`
   terminal. That closes D-1.
2. Then build `course-visuals` — the largest gap, and the first owner for L12 and L13.

Do not start `course-evidence`, the agents or the hooks before `course-visuals`; the blueprint's
order (§10) puts it first because it is the stated reason the factory exists.
