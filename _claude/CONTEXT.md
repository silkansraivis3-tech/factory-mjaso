# Working context — NOVIKONTAS Course Factory

For the next Claude session. Read this before touching anything in this repository.

**Status: Phase 1 complete, 2026-09-10. Architecture only. Awaiting owner review.**
No plugin, skill, agent or hook has been created. Phase 2 does not start until the blueprint is
approved and the six decisions in `docs/COURSE_FACTORY_BLUEPRINT.md` §9 are answered.

---

## What this repository is

The write target for the reusable Course Factory. Today it holds the Phase 1 architecture package and
nothing else.

```
00_READ_ME_FIRST.md
docs/COURSE_FACTORY_BLUEPRINT.md        what to build, and why each piece exists
docs/COURSE_PRODUCTION_PROCESS.md       how a course is made
docs/GOLDEN_COURSE_EXTRACTION.md        what GAS BASIC is and what is reusable
docs/ANDROID_INTEGRATION_CONTRACT.md    what the app requires
docs/FACTORY_RULE_CLASSIFICATION.md     every rule, sorted; contradictions named
_claude/CONTEXT.md                      this file
```

---

## Locations

| | | |
|---|---|---|
| Reference course | `C:\Users\raiviss\Desktop\docling\gas_basic\GAS Basic` | **READ ONLY** |
| Android application | `C:\Users\raiviss\AndroidStudioProjects\NOVIKONTASTraining` | **READ ONLY in this phase** |
| Existing skill bundle | `C:\Users\raiviss\Desktop\novikontas-course-skills` → `github.com/silkansraivis3-tech/course-factory` | source for migration |
| Installed skills | `C:\Users\raiviss\.claude\skills\` — five `course-*` folders, installed by **file copy, not as a plugin** | |
| Colleague handover | `C:\Users\raiviss\Desktop\course-factory-handover` | `install.ps1`, `new-course.ps1`, `FOR-YOUR-COLLEAGUE.md` |
| This repository | `github.com/silkansraivis3-tech/factory-mjaso` | **the only write target** |

The Phase 1 brief gave the reference course path as `docling\gas\_basic\GAS Basic`. The real path is
`docling\gas_basic\GAS Basic`. There is also an older, superseded `C:\Users\raiviss\Desktop\gas basic`
— **not** the reference course.

---

## The five facts that took longest to establish

1. **The factory already exists at about 70 %** — five skills at v1.3.0 in `course-factory`, with
   fifteen scripts and a publisher gate. Phase 2 is migration plus four additions, not a rewrite.
2. **The Android app is the delivery contract, and it is stricter than any document said.** Every
   host except `*.supabase.co` gets a 403 from the app itself; only `.html` can be navigated to;
   `target="_blank"` and `window.open` do nothing; hardware Back clicks `a.gbt-topback` or
   `.gbn-back` and exits the app if neither exists. See the Android contract.
3. **The decks are not in the APK.** `it_run.js` and `it_content.js` name
   `Module_0N/presentation/index.html`, but no `presentation/` folder exists under any asset root and
   no page links to one. Probably deliberate (projected from a laptop) — **not confirmed, do not
   assume.** Decision D-4.
4. **Three of eight shipped modules run a second token dialect**, produced by parallel module agents.
   This is the evidence behind gating `module-producer` and behind `course-visuals` existing at all.
5. **The build order depends on four `novikontas-*` skills that are not in the plugin** and arrive
   through a different distribution channel. A colleague installing the factory gets dangling
   references. Decision D-3.

---

## Rules in force

- The reference course, `source_files/`, `knowledge_base/` and the Android application are
  **read-only**. This repository is the only place to write.
- Do not copy the GAS BASIC course into this repository. Extract only what is genuinely reusable.
- **Never** bring the ICS/SIGTTO figures here. Six are marked *NOT cleared for issue or publication*
  and currently block the course itself from being issued.
- The Supabase **anon** key in `gb_config.js` is publishable by design; a `service_role` key is not.
  Neither belongs in this repository.
- The owner commits, publishes and installs. The factory builds and reports.
- Keep this repository small. Architecture, then a plugin — not a copy of a course.

---

## Contradictions recorded, not resolved

Eight, listed in `docs/FACTORY_RULE_CLASSIFICATION.md` §10. The ones that will bite first:

- **C-1** — three documents disagree about remote fonts, and the app's actual behaviour (403) matches
  none of them.
- **C-6** — `FOR-YOUR-COLLEAGUE.md` installs four skills and omits `course-module-ui`, which the build
  order makes required. `install.ps1` installs all five.
- **C-7** — `gb_tasks.js` claims to be both generated and hand-maintained.

---

## Open questions for the owner

`docs/COURSE_FACTORY_BLUEPRINT.md` §9, D-1 to D-6. **D-1** (does this repository supersede
`course-factory`?) and **D-3** (the `novikontas-*` dependency) change the shape of Phase 2 and should
be answered first.

Carried over from GAS BASIC and still open, because a new course will meet them again:
**R-02** practical activity inside nominal theory hours · **R-10** teaching aid A2 requires a
PowerPoint-format presentation while the system ships instructor-led HTML · the ICS/SIGTTO figure
clearance.

---

## Next session

Start with `00_READ_ME_FIRST.md`, then the blueprint. If the blueprint is approved, Phase 2 step 1 is
scaffolding the plugin and marketplace here and migrating the five existing skills **unchanged** —
change them only after they are installing and loading from this repository.

Do not begin by writing new skills. The container first, then the four additions.
