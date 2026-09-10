# Phase 2 migration report

**Scaffold the plugin and marketplace; migrate the five proven skills.** 2026-09-10.

Phase 2 was a migration, not a redesign. No proven rule was simplified, reworded or "cleaned up".

---

## 1 · Provenance — exactly what was migrated

| | |
|---|---|
| Source repository | `github.com/silkansraivis3-tech/course-factory` |
| Source working copy | `C:\Users\raiviss\Desktop\novikontas-course-skills` |
| Source path | `course-factory-plugin/skills/` |
| **Source commit** | **`4dc5ff97ee73c5e2ccab8c35a3dffdff6271d133`** (`4dc5ff9`) |
| Commit date | 2026-09-10T09:24:13+03:00 |
| Commit subject | *fix: route new modules through course-module-ui* |
| **Source plugin version** | **1.3.0** |
| Working copy state | clean — no uncommitted changes |
| **New plugin version** | **2.0.0** |
| Files migrated | **66** |
| Parity **at copy time** | **66/66 byte-identical by SHA-256** |
| Manifest hash of the copied set | `af85a35beb2300aaed61941beea18aa2051313e3b6c5f01c42f1a6546ed6e27c` |
| Parity **as shipped** | **64/66 byte-identical**, 2 files additively extended, 1 file added — the three deliberate D-3 changes in §3 and nothing else |

The source version is corroborated independently by the installer stamp at
`~/.claude/skills/.course-tools-version.json`, which records `version 1.3.0`, `revision 4dc5ff9`,
published 2026-09-10.

**The old repository was not touched.** Per D-1 it is a read-only migration source and stays that
way until parity and installation are both confirmed.

### Is the source the true latest?

Checked, because the bundle could have been edited in place after publication. Every file in
`~/.claude/skills/` was compared against the repository: **34 files reported as differing by `diff`,
and all 34 differ only in line endings.** After normalising, **zero content differences**. The
repository at `4dc5ff9` is the authoritative source.

The line endings run the way round you might not expect, and it is worth recording so a future
parity check is not misread: `core.autocrlf` is `true`, so the **local git checkout of the source
is CRLF** while the committed **blob is LF**; the PowerShell installer copied from the GitHub zip,
which serves the blob, so **`~/.claude/skills/` is LF**. Byte comparisons between a checkout and an
installed copy will therefore always differ, and always harmlessly.

### Parity proven at the blob level

Working-copy hashes depend on `core.autocrlf`, so the durable check compares **git blobs**, which
are line-ending-normalised on both sides. Source `HEAD` versus this repository's staged index:

| | |
|---|---|
| source blobs under `course-factory-plugin/skills/` | 66 |
| staged blobs under `plugin/skills/` | 67 |
| **blob-identical** | **64** |
| blob-differing | 2 — `course-factory/SKILL.md`, `course-factory/templates/factory-notes.md` |
| new | 1 — `course-factory/org/ORG_DEPENDENCIES.md` |

Those three are exactly the D-3 changes in §3 and nothing else. A `.gitattributes` with
`* text=auto eol=lf` now pins line endings, so this check stays meaningful on any machine.

---

## 2 · What was created

```
factory-mjaso/
  .claude-plugin/marketplace.json          novikontas-course-factory
  plugin/
    .claude-plugin/plugin.json             course-factory 2.0.0
    CLAUDE.md                              16 global laws, one line each
    skills/                                the five migrated skills, byte-identical
      course-factory/org/ORG_DEPENDENCIES.md    NEW - the D-3 fallback
    resources/README.md                    what belongs here, and why it is empty in 2.0.0
```

---

## 3 · Changes to migrated content — three, all additive, all deliberate

Nothing was removed, reworded or renamed. Three files gained content, each required by owner
decision **D-3**:

| # | File | Change | Why |
|---|---|---|---|
| M-1 | `skills/course-factory/org/ORG_DEPENDENCIES.md` | **new file** | D-3 requires a documented fallback owned by the Course Factory. Classifies all 12 distinct `novikontas-*` references and carries three minimal fallbacks. |
| M-2 | `skills/course-factory/SKILL.md` | **+11 lines**, one new subsection after the boundary table | The router must say what to do when an organisation skill is absent. Nothing existing was altered. |
| M-3 | `skills/course-factory/templates/factory-notes.md` | **+12 lines**, new §0 | D-3 requires the chosen route to be recorded per run. The template had no place to record it. |

`course-module-ux`, `course-module-ui`, `course-task-ux` and `course-tablet-publisher` are
**untouched — byte-identical to source.**

### No compatibility change was needed

The most likely breakage was path resolution, and it did not occur:

- **Every script resolves paths from `__file__`**, never from an absolute path and never from
  `~/.claude/skills`. Verified across all 15 Python scripts.
- **Cross-skill resolution already anticipated the plugin layout.** `publish.py` resolves
  `course-factory` as `os.path.dirname(SKILL_ROOT)/<name>`, and its own docstring says this holds
  "whether both are user skills in `~/.claude/skills/` or both are inside a plugin's `skills/`
  folder". Tested in the new layout: it resolves, and `course-factory/tablet/GUIDE.md` is reachable.
- **No `${CLAUDE_SKILL_DIR}` usage anywhere** — nothing to re-point.
- **No absolute machine paths.** `platform.json`'s `path_hints` use `~/`-relative forms by design
  and the file states there is no fixed path.
- `serve_fresh.py` keeps its port state in `~/.course_module_ux_used_ports.json`, outside the skill
  directory — correct for a plugin install, where the plugin directory is a managed cache.

---

## 4 · Organisation-skill dependencies (D-3)

Every `novikontas-*` reference in the bundle was found and classified. Full table in
`plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`.

| Class | Skills | Handling |
|---|---|---|
| **Blocking** | `novikontas-pedagogy-toolkit`, `novikontas-handouts`, `novikontas-course-start` | One minimal fallback each (F/B, F/C, F/A). Each states what it does **not** cover. |
| **Soft** | `novikontas-course-intake`, `-course-plan`, `-brandbook`, `-presentations`, `-course-start-page`, `-written-tests`, `-practical-exercises`, `-exercise-description-trainee`, `-skill-conventions`, `-token-economics` | Pointer rows. Name the owner, answer within the factory's own rules, record it. No fallback needed. |
| **Not a dependency** | `novikontas-training-app` (a GitHub repository name), `novikontas-brandbook` in two CSS comments (provenance of a colour) | Ignore. |

No organisation-skill content was duplicated.

---

## 5 · Validation

### 5.1 What could not be run, and why

**`claude plugin validate --strict` was not run.** The Claude Code CLI is not installed on this
machine: it is not on `PATH` for either shell, and the only `claude.exe` present
(`%LOCALAPPDATA%\AnthropicClaude\claude.exe`, version 1.49585.0) is the desktop application, which
does not implement the `plugin` subcommands — invoking `plugin validate --help` produced no output
and no exit code.

**Marketplace installation was not performed.** `ListPlugins` returns empty, `~/.claude/plugins/`
does not exist, and there is no `settings.json` — this machine has never installed a Claude Code
plugin. The documented flow (`/plugin marketplace add`) needs an interactive session, which this is
not. **Installation is therefore unverified and is the first thing to confirm in Phase 3.**

Nothing was faked. No Claude configuration file was edited to simulate an install.

### 5.2 What was run

A structural validator was written against the rules documented at
`code.claude.com/docs/en/plugins-reference` and `/plugin-marketplaces` (checked 2026-09-10). It is a
stand-in for the official validator, not a replacement, and it is deliberately not committed —
it is a Phase 2 check, not a factory asset.

**Result: 22 passed · 9 warnings · 0 failures.**

| Check | Result |
|---|---|
| `marketplace.json` parses; `name` kebab-case; `owner` object with `name`; `plugins[]` entries carry `name`+`source` | PASS |
| plugin source `./plugin` is relative, `./`-prefixed, resolves inside the marketplace root | PASS |
| `plugin.json` parses; `name` kebab-case; no unrecognised fields; **version is 2.0.0** | PASS |
| marketplace entry name matches `plugin.json` name | PASS |
| `.claude-plugin/` contains **only** `plugin.json`; no component directory inside it | PASS |
| `skills/` at plugin root; all five skills present; every `SKILL.md` has valid frontmatter with `name` matching its folder | PASS |
| no absolute machine-specific paths | PASS |
| no `.bak` / `.orig` / `.pyc` / `__pycache__` | PASS |
| no credential patterns | PASS |

Skill `description` lengths: 787–1198 characters, all inside the ~1,536 budget.

### 5.3 Scripts still run — and still behave

All nine entry-point scripts import and parse arguments from the plugin location. Two were driven
against synthetic fixtures to prove *behaviour*, not merely startup:

| Test | Expected | Got |
|---|---|---|
| `audit_ui.py` on the migrated `gb_tokens.css` — proves it loads its sibling `knowledge/tokens.json` | reads, 0 defects | *"1 stylesheets read - 0 defects"* — PASS |
| `publish.py sibling_skill("course-factory")` in the plugin layout | resolves to the sibling skill | resolved; `tablet/GUIDE.md` reachable — PASS |
| `verify_links.py` on a tree with **one planted dead link** | finds it, exit 1 | *"DEAD: 1 distinct target(s)"*, exit 1 — PASS |
| `audit_navigation.py` on the same tree | reachable, way back present, exit 0 | exit 0 — PASS |
| `check_hours.py` on an **exact** synthetic plan | 1:1, exit 0 | *"minutes are 1:1 with the accredited programme"* — PASS |
| `check_hours.py` on a plan **+40 min over** | fails, names the module, exit 1 | *"module 2 is +40 min against its allocation"*, exit 1 — PASS |

The last two matter most: L1 is the flagship law and it still fires with the right message.

Fixtures were synthetic. **No course content or knowledge base was read in this phase**, as
instructed.

### 5.4 The nine warnings — all correct-by-design, one worth acting on

Every warning is a documentation reference to a file that is deliberately **outside** the plugin.

| Reference | Verdict |
|---|---|
| `coverage/verify_all.py` (course-factory MANIFEST) | provenance — names the GAS BASIC working-area script `verify_course.py` was generalised from. Correct. |
| `Module_01/presentation/presentation.css` ×2 | pointers into the golden reference course, which is deliberately not in the plugin. Correct. |
| `courses/registry.js`, `gb_courses.js`, `server/courses.json`, `training_terminal/…` ×5 | files in the Android platform repository. Correct. |
| `gas-basic-module-ux/reference/QA_CHECKLIST.md` | mostly a dedup/provenance record of a **superseded** skill — but `MANIFEST.md` line 158 also states the record-engine files "remain in `gas-basic-module-ux/assets/` as the only copies". **That skill no longer exists.** |

**F-2 · Pre-existing gap, not introduced by migration.** `course-module-ux/build/GUIDE.md` §8
teaches how to choose a record engine without shipping the code, and points at a skill that is gone.
Left unchanged, per *do not silently fix behavioural differences during migration*. It is a
candidate for `resources/engines/` in Phase 3.

### 5.5 The published repository resolves as a GitHub-hosted marketplace

Run against a **fresh `git clone` of the pushed repository**, so nothing could depend on the local
working copy. This exercises the whole data path of
`/plugin marketplace add silkansraivis3-tech/factory-mjaso` — everything except the installer binary
itself.

```
marketplace name : novikontas-course-factory
owner            : Novikontas Academy
plugin entry     : course-factory  source=./plugin
  resolves to    : OK  (inside marketplace root: True)
  plugin.json    : name=course-factory  version=2.0.0
  skills found   : 5
     /course-factory:course-factory             SKILL.md OK
     /course-factory:course-module-ui           SKILL.md OK
     /course-factory:course-module-ux           SKILL.md OK
     /course-factory:course-tablet-publisher    SKILL.md OK
     /course-factory:course-task-ux             SKILL.md OK
```

From that same fresh clone, `audit_ui.py` read its sibling `knowledge/tokens.json` and reported
`1 stylesheets read - 0 defects`, and `publish.py` resolved the sibling `course-factory` skill with
`tablet/GUIDE.md` reachable. **The five skills will be namespaced `/course-factory:<skill>` once
installed** — worth knowing before looking for the old unnamespaced names.

### 5.6 Nothing else was modified

| | |
|---|---|
| GAS BASIC course tree | **untouched** — never opened for writing |
| Android project | **untouched** — `git status` clean, `HEAD 24b35f0` |
| `course-factory` repository | **untouched** — `git status` clean, still at `4dc5ff9` |
| `~/.claude/skills/` | **untouched** — no file modified since the session began |

All four verified after the push, not assumed.

---

## 6 · Findings

**F-1 · A plugin-root `CLAUDE.md` is not loaded.**
`code.claude.com/docs/en/plugins-reference` states plainly: *"`CLAUDE.md` at plugin root is **NOT**
loaded as project context; use skills instead."* Phase 2 was instructed to create
`plugin/CLAUDE.md` and did — but implementing it silently would have shipped an authoritative-looking
file that never reaches a session, which is exactly the class of defect this project keeps recording.

The file therefore says so at the top, and every law names the skill that already enforces it, so the
content does reach a session by the route that works. **Fourteen of the sixteen laws have an owning
skill today. L12 (asset provenance) and L13 (animation must explain a mechanism) do not** — their
owner is `course-visuals`, in Phase 3.

*Options for Phase 3, for the owner to choose:* fold the cross-cutting laws into `course-factory`'s
SKILL.md (loads whenever the router does, but not when a specialist skill is entered directly); a
small always-on laws skill (a sixth surface); or a `SessionStart` hook injecting them as
`additionalContext` (deterministic, but hooks were out of scope for Phase 2).

**F-2 · Record-engine code points at a deleted skill.** See §5.4.

**F-3 · The personal skills will coexist with the plugin skills.** The five folders in
`~/.claude/skills/` are plain skills with no manifest. Once the plugin is installed, plugin skills
are namespaced (`/course-factory:course-factory`) and the documentation states the unnamespaced
original and the plugin copy **both remain available** — they do not shadow each other. Two copies of
the same skill, one of them frozen at 1.3.0, is a drift source. Removing the personal copies is part
of confirming the switchover, and it is the owner's action, not the factory's.

---

## 7 · Installation — the exact flow, for the owner to run

Not yet executed (§5.1). In an interactive `claude` terminal:

```bash
claude plugin validate <path-to>/factory-mjaso/plugin --strict
```

```bash
claude --plugin-dir <path-to>/factory-mjaso/plugin
```

Then, from the published repository:

```
/plugin marketplace add silkansraivis3-tech/factory-mjaso
/plugin install course-factory@novikontas-course-factory
```

### Acceptance checklist

- [ ] `claude plugin validate --strict` prints `✔ Validation passed`
- [ ] `/plugin` shows **course-factory 2.0.0** from **novikontas-course-factory**
- [ ] all five skills appear namespaced: `/course-factory:course-factory`,
      `:course-module-ux`, `:course-module-ui`, `:course-task-ux`, `:course-tablet-publisher`
- [ ] the **Errors** tab in `/plugin` is empty
- [ ] `python <plugin>/skills/course-factory/hours/scripts/check_hours.py --help` runs from the
      installed cache path
- [ ] the five personal copies in `~/.claude/skills/` are removed once the plugin is confirmed (F-3)

**Versioning note.** Claude Code pins a git-sourced plugin to its `version` string. Every release
must bump `plugin.json`'s `version` or installed copies will not update.

---

## 8 · Blocking Phase 3

1. **Installation is unverified** (§5.1). Confirm it before treating `factory-mjaso` as
   authoritative — D-1 makes parity *and* installation the condition, and only parity is proven.
2. **F-1** — decide how the global laws reach a session.
3. **L12 and L13 have no enforcing skill** until `course-visuals` exists.
4. **D-2, D-4, D-5, D-6** from the blueprint remain open. D-5 (raise the remote-font check to
   `FAIL` for new courses) is a change to `course-tablet-publisher` and was deliberately **not**
   made here — Phase 2 was migration only.
