# Phase 3 — the instructional visual system

**Plugin 2.0.0 → 2.1.0.** 2026-09-10.

Phase 3 closed the two holes this project was started for: nothing owned **what representation
teaches a concept**, and nothing owned **where the asset comes from**. It also resolved findings
**F-1** and **F-4**.

---

## 1 · Version — why 2.1.0

**MINOR.** Additive and backwards compatible: a new skill, a new agent, a new resources folder, and
one new step in the build order. No existing skill's rules changed, no script's interface changed,
and every previously valid course project remains valid.

Not PATCH — this adds a production capability. Not MAJOR — nothing that worked before now breaks.
Removing `plugin/CLAUDE.md` is not a breaking change because Claude Code never loaded it; that is
the whole content of F-1.

Claude Code pins a git-sourced plugin to its `version` string, so the bump is also what makes the
release reach installed copies at all.

---

## 2 · What the reference course showed

Read on 2026-09-10, for **visual production knowledge only**. No maritime content was audited and
nothing was modified.

| Finding | Measurement |
|---|---|
| Stepped reveal is the dominant teaching idiom | `data-step` **373** occurrences · `replay` **282** |
| Canvas is used in **zero** teaching visuals | 8 modules, no `getContext` in any deck |
| Visual investment is wildly uneven | M01: 90 inline SVG, 21 keyframes · M02 deck: 0 SVG · M05: 159 card classes, 0 deck SVG |
| **Engines are copy-pasted, not shared** | M04 and M07 each carry **4 dead visualisation engines** copied from M01, self-disabling because the host elements do not exist. M01's own quiz engine is dead too. |
| Motion mixes three categories with no naming | teaching (`svpMerc`/`svpNeedle`/`svpUp`/`svpVap`) · ambient (`wvDrift*`, `vpDrift*`, `fleetA/B`) · chrome (`slideIn`, `pulseDot`) |

**The strongest artefact** is a seven-step vapour-cloud sequence: `data-step` layers revealed
cumulatively, one caption per step, play/pause/step/replay, an `enter`/`leave` lifecycle so it does
not run off-screen, and its evidence cited in the code banner. One of its seven steps exists purely
to **correct a misconception the learner arrives with**. That became the second-commonest
legitimate animation pattern in `decide/GUIDE.md`.

**The strongest technical figure** is a cargo schematic generated from a typed segment table
(`SEG = { id -> {d, kind} }`) with liquid and vapour services distinguished, tanks drawn showing
their phase split, and real spatial arrangement. It is the counter-example to boxes and arrows, and
it became `resources/patterns/system-schematic/`.

**The weak examples** are equally useful: Module 5 carries 159 card classes and no deck SVG at all —
text in boxes where the subject is equipment. `check_visuals.py` detects that shape by name.

No GAS BASIC subject matter was copied into the factory. The three shipped engines are clean
re-implementations of the mechanisms, not copies carrying the reference course's content.

---

## 3 · `course-visuals`

**Owns: what representation best teaches the concept, and where the asset comes from.** Nothing
else — it does not restate a colour, a radius, a contrast ratio, a tap size or an overflow rule.

```
SKILL.md                        router · learning-first law · animation law · L12/L13
decide/GUIDE.md                 learning need -> representation -> storyboard
  knowledge/learning-needs.json     15 needs, candidates, avoid-list, a test each
  knowledge/representations.json    20 representations + 6 named non-representations
source/GUIDE.md                 the 4-level pipeline, rights, provenance
  knowledge/asset-pipeline.json     levels, authority ranking, 6 rights states
  schemas/_photo_meta.schema.json · _figure_meta.schema.json
  schemas/GENERATED_ASSET_BRIEF.md  the contract for a future image-generation MCP
review/GUIDE.md                 the gate that asks whether it teaches
  knowledge/motion-rules.json       categories, four questions, 9 rejected patterns
  knowledge/visual-floor.json       measurable floor + 14 human review questions
scripts/resolve_asset.py · check_visuals.py · check_assets.py
templates/VISUAL_STORYBOARD.md · visual-notes.md
MANIFEST.md
```

### The boundary, as implemented

| Skill | Owns |
|---|---|
| `course-module-ui` | how a page **looks like a NOVIKONTAS page** |
| `course-module-ux` | how the **delivery works** |
| `course-task-ux` | how a trainee **answers** |
| **`course-visuals`** | **what the picture should be** |

The line that gets blurred: `course-module-ui` owns the **card as a component**. Using cards as the
*answer to a teaching need* is `course-visuals` failing to name the need.

### Three lanes, not four

Animation is a representation choice, so its **law** sits in SKILL.md (where it always loads), its
**design mechanics** in `decide/`, and its **rejection checklist** in `review/`. A fourth lane would
have split one decision across two places.

---

## 4 · L12 and L13 now have an owner

Both were stated in the plugin-root `CLAUDE.md` and enforced nowhere.

**L13 · the animation law.** Motion is instructional only when it explains movement, flow, state
change, sequence, mechanism, cause and effect, spatial relationship, progression over time or system
response. Every substantial animation answers four questions **in the storyboard, before it is
built** — what changes, why, what should the learner notice, what should they understand afterwards.
*The failure signature:* if question 4 is answered by the caption alone with the motion removed, the
motion is not carrying the teaching.

Nine patterns are rejected by name, so a review can point at the name instead of arguing about
taste — including **"motion added only because animation was requested"**.

Every non-chrome animation declares `data-motion="teaching" | "affordance" | "ambient"`. Ambient is
capped at one effect per screen and banned on a screen carrying a teaching animation.

**L12 · asset provenance.** Every asset carries provenance, a licence and a visual verification in a
metadata file **beside the file**, never a central register. Unclear rights are
`RIGHTS_REVIEW_REQUIRED` and block shipping.

---

## 5 · The asset pipeline

`1 PROJECT → 2 FACTORY → 3 INTERNET → 4 CREATE`, and **a level is exhausted only when it has been
searched**.

`resolve_asset.py` mechanises levels 1–2, including the term expansion that stops the commonest
failure — declaring an asset unavailable after one narrow grep. It expands to plurals, hyphenation,
abbreviations, and both British and American spellings, and reports the terms it tried.

Level 3 is judgement, with an authority ranking (manufacturer → official organisation → original
manual → recognised technical body → other credible source) and an explicit **not-authority** list
(SEO farms, aggregators, scrapers, stock previews, AI image sites). It belongs to `visual-sourcer`.

Two escalations, neither silent: **`RIGHTS_REVIEW_REQUIRED`** blocks shipping;
**`GENERATED_ASSET_REQUIRED`** emits a complete generation brief.

**No image-generation MCP was added**, deliberately. The brief is the contract for when one exists,
and it is useful immediately — a human can take it to any generator or commission a photograph from
it. Two hard limits survive into it: never for safety-critical equipment a learner must recognise,
and never in place of a structured technical schematic.

---

## 6 · `visual-sourcer`

Isolated-context agent. Tools: Read, Glob, Grep, Bash, WebSearch, WebFetch, Write. Preloads
`course-visuals`.

**Investigation only.** It never designs curriculum, edits course content, makes an ILO decision or
modifies an authoritative source. It searches levels 1→2→3, evaluates candidates for technical
credibility, records provenance and rights, downloads and packages anything it recommends, and
returns a short structured report — or `GENERATED_ASSET_REQUIRED` with a brief.

Isolation earns its place here: a thorough asset search is verbose, reads many pages, and returns
one paragraph of conclusion. The reference course already ran this shape by hand
(`IMAGE_BRIEF.md` → a fresh session → `IMAGE_DELIVERY.md`) and it worked.

---

## 7 · `resources/patterns/`

Three engines, course-agnostic, ES5, dependency-free, token-driven.

| Pattern | Solves |
|---|---|
| **photo-pins** | annotation in **image space**, so it survives a re-crop or a replaced photograph |
| **stepped-process** | the default shape of a teaching animation — `data-step` layers, one caption per step, play/pause/step/replay, pauses off-screen, honours reduced motion |
| **system-schematic** | a system rendered from a **typed topology** instead of boxes and arrows; flow drawn along the real route; and `downstream()`, so the model can be **asked** what is still connected if a valve shuts |

These exist because the reference course invented each once and then copy-pasted it, leaving eight
dead engines behind. One canonical copy is the fix.

---

## 8 · F-1 resolved

`plugin/CLAUDE.md` **removed**. Its content is now `docs/FACTORY_LAWS.md`, marked plainly as
documentation, with each law naming the skill that enforces it.

The official validator had confirmed the finding in almost the words the Phase 2 docs predicted:

```
‼ root: CLAUDE.md at the plugin root is not loaded as project context.
  To ship context with your plugin, use a skill instead.
× Validation failed (--strict treats warnings as errors)
```

After the move:

```
claude plugin validate .../plugin --strict
√ Validation passed          exit 0
```

Nothing was lost. L1–L11 and L14–L16 were already enforced in their owning skills; L12 and L13 now
have `course-visuals`. **All sixteen laws have an enforcing skill for the first time.**

## 9 · F-4 resolved

`Desktop/course-factory-handover/` installed a frozen v1.3.0 copy into `~/.claude/skills/` — a
directory the plugin no longer uses — and its instructions listed only four of the five skills,
omitting `course-module-ui`, which the build order makes required.

- `install.ps1` and `publish-skills.ps1` **retired**: they now print the marketplace instructions
  and exit 1 without installing or publishing anything.
- `FOR-YOUR-COLLEAGUE.md` **rewritten** for the plugin flow, including how to install the CLI, and
  an explicit instruction to delete the old `course-*` folders.
- Originals preserved in `_superseded_2026-09-10/`.
- The authoritative copy is now `docs/INSTALL_FOR_COLLEAGUES.md` in this repository, so it cannot
  drift out of sight again.
- `new-course.ps1` kept — it scaffolds a course project and is unrelated to skill installation.

---

## 10 · Validation

| Test | Expected | Result |
|---|---|---|
| `claude plugin validate --strict` | pass | **PASS**, 0 warnings (was 1 before F-1) |
| Structural check, marketplace + plugin schema | 0 failures | **PASS** |
| Asset pipeline — **project asset wins** | LEVEL 1, exit 0 | **PASS**, level 2 not even searched |
| Asset pipeline — **factory wins when project absent** | LEVEL 2, exit 0 | **PASS** |
| Asset pipeline — **nothing exists** | `GENERATED_ASSET_REQUIRED`, exit 3 | **PASS** |
| Provenance, complete record | exit 0 | **PASS** |
| Provenance, broken record | 6 failures incl. missing fields, invalid rights state, orphan image, generated illustration with no `generated_by` and not declared as a drawing | **PASS**, exit 1 |
| **Rights escalation** | `RIGHTS_REVIEW_REQUIRED` blocks | **PASS** — reported BLOCK, "this asset must not ship" |
| **Animation rejection** | decorative motion, no reduced-motion guard, box-and-arrow chain, card grid, remote asset, tiny SVG label | **PASS**, 2 failures + 7 warnings, exit 1 |
| Well-built teaching animation | clean | **PASS**, 0 findings, exit 0 |
| Shipped patterns pass their own checks | clean | **PASS**, 0 findings |
| Existing five skills, all scripts | 15/15 execute | **PASS** |
| `check_hours.py` regression | still fails a bad plan by name | **PASS**, exit 1 |
| `audit_ui.py` regression | clean on its own tokens | **PASS**, exit 0 |
| GAS BASIC / Android / old repo | unmodified | **PASS**, verified after the fact |

Two real bugs were found by these tests and fixed:

1. `check_visuals.py` crashed reading `svg_label_min_px`, which is an object documenting the value
   rather than a bare number.
2. The teaching-controls check fired on a **stylesheet**, which mentions `data-step` in a selector
   and can never contain a play button. Restricted to HTML — a check that cries wolf gets ignored.

The box-and-arrow and card-grid checks were also rewritten after the first run: counting arrows and
figures per page let an unrelated hero image excuse a chain sitting under it. They now match the
**structure** (`B A B A B`) rather than counting, and both fire correctly.

All fixtures were synthetic and deleted. **No course was created and no knowledge base was read.**

---

## 11 · Remaining limitations

- **Nothing here has been run against a real new course.** Every test was synthetic. The first real
  module is the actual test, and the most likely thing to need adjustment is the storyboard's weight
  for a small module.
- `check_visuals.py` reads **static** markup. A figure assembled by JavaScript at runtime is
  invisible to it — the same blind spot `audit_navigation.py` found for JS-built navigation. **The
  human review is not optional**, and the script says so in its own output.
- The decorative-vocabulary check is a **question, not proof**. A `pulse` can legitimately indicate
  a state change; it warns and a human decides.
- The rendered-SVG-label check assumes a 380 px column. It catches the common case and will miss an
  unusual layout.
- **`course-evidence` does not exist yet**, so `NO SOURCE = NO MARITIME CLAIM` still has no
  general owner — only the GAS-BASIC-specific retrieval skill.
- **No deterministic hooks.** Most laws still depend on the model remembering them.
- **F-2 is still open** — the record engines point at the superseded `gas-basic-module-ux`. Closing
  it is the `resources/engines/` job.
