# course-visuals — maintainer file

Not loaded at runtime. Why this skill exists, what it deliberately does not do, and what was
measured to justify it.

**v1 · 2026-09-10 · plugin `course-factory` 2.1.0 · Phase 3**

---

## Why it exists

The four migrated skills cover whether a screen **works** (`course-module-ux`), whether it **looks
like a NOVIKONTAS page** (`course-module-ui`), how a trainee **answers** (`course-task-ux`) and
whether the course **adds up** (`course-factory`). None of them decides **what the picture should
be**.

That gap is where generic AI course material comes from. Asked for a course graphic with no owner
for the decision, the default output is a row of cards, three boxes joined by arrows, an icon, a
gradient and something that pulses.

It is also the owner for laws **L12** (asset provenance) and **L13** (animation must explain a
mechanism), which until Phase 3 had no enforcing skill and depended on a plugin-root `CLAUDE.md`
that Claude Code does not load.

## The boundary, stated once

| Skill | Owns |
|---|---|
| `course-module-ui` | how a page **looks like a NOVIKONTAS page** — tokens, type, cards, semantic colour |
| `course-module-ux` | how the **delivery works** — composition, fill, overflow, the screen floor, the run script |
| `course-task-ux` | how a trainee **answers or completes** |
| **`course-visuals`** | **what representation best teaches the concept**, and where the asset comes from |

The line that gets blurred: `course-module-ui` owns the **card as a component**. Using cards as
the *answer to a teaching need* is `course-visuals` failing to name the need. Neither skill should
restate the other.

`course-visuals` deliberately does **not** restate a single colour, radius, contrast ratio, tap
size or overflow rule. It cites the floor in `course-module-ux` and the tokens in
`course-module-ui`.

## What the reference course showed, measured

Read 2026-09-10 across eight modules. Numbers, not impressions:

| Finding | Measurement |
|---|---|
| Stepped reveal is the dominant teaching idiom | `data-step` — **373** occurrences; `replay` — **282** |
| Canvas is used in **zero** teaching visuals | 8 modules, 0 `getContext` in any deck |
| Visual investment is wildly uneven | M01 90 inline SVG / 21 keyframes · M02 0 SVG in its deck · M05 159 card classes, 0 deck SVG |
| Engines are copy-pasted, not shared | M04 and M07 each carry **4 dead visualisation engines** copied from M01, self-disabling because the host elements do not exist. M01's own quiz engine is dead too. |
| Motion mixes three categories with no naming | teaching (`svpMerc`/`svpNeedle`/`svpUp`/`svpVap` — four properties animating one causal story) · ambient (`wvDrift*`, `vpDrift*`, `fleetA/B`) · chrome (`slideIn`, `pulseDot`) |

The strongest single artefact is the seven-step vapour-cloud sequence: `data-step` layers, one
caption per step, play/pause/step/replay, `enter`/`leave` lifecycle, evidence cited in the banner —
and **one of its seven steps exists purely to correct a misconception the learner arrives with**.
That is the pattern `decide/GUIDE.md` names as the second-commonest legitimate animation.

The strongest technical figure is a piping schematic generated from a typed segment table
(`SEG = { id -> {d, kind} }`), with liquid and vapour services distinguished, tanks drawn showing
their phase split, and real spatial arrangement. It is the counter-example to boxes and arrows,
and it became `resources/patterns/system-schematic/`.

## Structure

```
SKILL.md                        router · the learning-first law · the animation law · L12/L13
decide/GUIDE.md                 learning need -> representation -> storyboard
  knowledge/learning-needs.json     15 needs, candidates, what to avoid, a test each
  knowledge/representations.json    20 representations + 6 named non-representations
source/GUIDE.md                 the 4-level pipeline, rights, provenance
  knowledge/asset-pipeline.json     levels, authority ranking, 6 rights states
  schemas/*.schema.json             _photo_meta / _figure_meta contracts
  schemas/GENERATED_ASSET_BRIEF.md  the contract for a future image-generation MCP
review/GUIDE.md                 the quality gate that asks whether it teaches
  knowledge/motion-rules.json       categories, four questions, 9 rejected patterns
  knowledge/visual-floor.json       measurable floor + 14 human review questions
scripts/resolve_asset.py        pipeline levels 1-2, mechanically
scripts/check_visuals.py        deterministic visual checks
scripts/check_assets.py         provenance, licences, rights
templates/                      VISUAL_STORYBOARD.md · visual-notes.md
```

## Deliberate omissions

- **No image-generation MCP.** `GENERATED_ASSET_REQUIRED` plus a complete brief is the contract; a
  server can be added later without changing the skill. Most technical figures should be authored
  SVG anyway.
- **No Canvas helper.** The reference course needed none in eight modules of technical teaching.
- **No colour, type or spacing rules.** `course-module-ui` owns those and a copy would go stale.
- **Level 3 of the pipeline is not automated.** Judging whether a source is technically credible is
  not a regex. It belongs to the `visual-sourcer` agent.

## Known limits

- `check_visuals.py` reads **static** markup. A figure assembled by JavaScript at runtime is
  invisible to it, exactly as `audit_navigation.py` found for JS-built navigation. The human review
  is not optional.
- The decorative-vocabulary check is a **question, not proof** — a `pulse` can legitimately be a
  state indicator. It warns; a human decides.
- The rendered-SVG-label check assumes a 380 px column. It catches the common case (a label sized
  in viewBox units without thinking about scale) and will miss an unusual layout.
- **Nothing here has been run against a real new course yet.** Everything was validated on
  synthetic fixtures. The first real module is the test.

## Token cost

Always-on ~330 (the description). On invoke, SKILL.md only; each lane is read on demand.
Three lanes, not four — animation is a representation choice, so its law sits in SKILL.md, its
design mechanics in `decide/`, and its rejection checklist in `review/`, rather than earning a
lane of its own.
