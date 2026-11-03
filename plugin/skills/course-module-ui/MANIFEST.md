# course-module-ui — maintainer notes

Created 2026-09-09, after the owner asked why four course skills covered UX and none covered
how anything looks.

## Why it exists

`course-module-ux` owns a **floor** — `floor.json` is contrast ≥ 4.5, text ≥ 12.5 px, targets
≥ 44 px, fill 85–100 %, no spill. Every one of those is a minimum. None of them says what
colour, what typeface, what a header band is. Two people could pass the whole audit and ship
courses that look unrelated.

They did. See *Findings*.

## What was measured, and how

Everything in `knowledge/tokens.json` and `references/anatomy.md` was extracted from the
shipped GAS BASIC course on 2026-09-09 by script, not written from memory:

- 85 stylesheets, 1.44 MB of CSS, across 8 modules
- 12 of those are deck stylesheets (`presentation/` or `instructor_screens/`)
- `tokens.json` and `templates/gb_tokens.css` are both **generated** from
  `Module_01/presentation/presentation.css`, so they cannot disagree with each other

Module 1 is canonical because the owner ruled it the UX/UI reference on 2026-09-01. That
ruling was about interface; extending it to the visual layer is this skill's inference from
it, not a second ruling — if the owner disagrees, the canonical source changes and both
generated files are rebuilt from the new one.

## Findings recorded at build time

| Finding | Detail |
|---|---|
| Two dialects | Modules 04, 07, 08 match the reference exactly. Modules 03, 05, 06 rename four wash tokens to `-soft-`, miss 16 canonical tokens, and differ on 10 values by a shade. |
| Radius names split | Reference uses `--r-l/-m/-s`; 19 other files use `--r-lg/-md/-sm`. Same values, two vocabularies. Aliased, not renamed. |
| No `:root` at all | Every `gb_review.css` inherits whatever loaded first. |
| Tokens barely adopted | The reference module itself carries 134 raw chrome colours (81 distinct) outside `:root`. The system is real but partial. |
| Hazard colours missing | 03/05/06 invented `--red`, `--flame`, `--toxic`. A gas course needs them; the reference set has none. Left as an open question, deliberately unresolved. |

## Deliberate omissions

**No auto-fix.** The obvious next feature is `--fix` to rewrite drifted values. It is not here
on purpose: repainting a signed-off, accredited deck is a content decision. The script reports
and names files; a human decides.

**`--strict` is off by default.** A gate that fails all eight shipped modules on day one is a
gate people learn to ignore. Default is a report; `--strict` is for new decks and does exit 1.

**Nothing about the handout or task palettes.** Tasks and handouts measurably run their own
colour sets (tasks lead with `#fffbf1`/`#0f6047`, handouts invert the deck's navy/amber
emphasis and use a 16 px radius). Whether that is intentional design or more drift was not
established, so this skill does not rule on it. That is the first thing to settle next.

## Wired into the pipeline, 2026-09-10

This skill shipped in the bundle on 2026-09-09, but nothing routed to it: no step of
`course-factory/knowledge/build-order.json` named it and `course-factory/SKILL.md` never
mentioned it, so it only ran if someone remembered to ask for it by name. A module could pass
the hours law, the coverage check, the link and navigation audits and the whole `course-module-ux`
measurement lane and still ship looking like default white HTML.

It is now step **8** of that build order (*establish the visual system*, before any HTML exists)
and part of step **15** (verify), where `audit_ui.py --strict` is the visual sign-off for new
work. See the repository README for the change record.

## Copied, never read — 2.11.1 (2026-09-30, Phase 5 step 11b)

Setting up a module's look used to mean reading about 82 KB of files (this `SKILL.md`,
`tokens.json`, `anatomy.md`, and the style files `gb_tokens.css`, `gb_shell.css`, `gb_compose.css`,
`gb_shell.html`) — roughly 20,600 tokens — of which the style files, about 58 KB, only ever needed
to be **copied**. Owner decision: a script copies them, the model reads a short vocabulary instead,
and a check proves the copies identical.

| file | job |
|---|---|
| `knowledge/design-system.json` | the list of canonical files every module carries in `assets/`, and where each comes from (edit the list, not the script) |
| `scripts/design_system.py install` | copies them byte for byte; `--start-deck` writes `module.html` from the frame if there is none; refuses to overwrite a differing file without `--update`; refuses anything inside the Android project (L21); writes `_factory/design_system.json` |
| `scripts/design_system.py check` | OK / MISSING / OUTDATED (the factory's file improved since) / CHANGED (edited in the module) |
| `references/vocabulary.md` | every composition, component, page and task class and every token, by name and when to use it |
| `scripts/test_design_system.py` | copy, catch, never-overwrite, Android refusal, the record is INTERNAL to the publisher — and **vocabulary completeness**: every class and token in the style files is named, nothing named is invented |

The completeness test earned its place on its first run: it found `.caption` in `gb_compose.css`,
which the hand-written vocabulary had missed. `course-tablet-publisher`'s `internal_globs` gained
`(^|/)_factory/` in the same change — the expert-edit build record already lived there and was not
covered. `anatomy.md` and `tokens.json` stay: read only when a component itself is being built or
changed, or when a value itself is the question.

## The factory's own files pass the strict check — 2.11.2 (2026-09-30, Phase 5 step 11c)

Until 2.11.2 the factory's own shared files failed `audit_ui.py --strict`, which meant every
correctly built new module failed its sign-off on files it did not write. Owner decision: fix at
the source, never teach the check to skip files. 128 raw chrome colour uses in four files
(`gb_compose.css` 8, `gb_shell.css` 10, `course-module-ux/assets/gb_run.css` 108,
`course-task-ux/assets/task_complete.css` 2) became 78 named custom properties in each file's own
`:root` — prefixes `--cmp-`, `--shl-`, `--run-`, `--task-` — holding the exact text that was inline.
They are file-local, not canonical tokens: each file keeps working on its own, and the canonical
set (and `references/vocabulary.md` §8) did not grow by 78 names nobody builds with.

Proven identical three ways: (1) putting each token's value back reproduces every original file
exactly; (2) specimen pages with an element for every selector those files style, opened before
and after in headless Chrome — 0 of ~464,000 computed values differ; (3) the same pages'
screenshots are identical pixel for pixel. A deliberate one-shade change to one token was caught by
both (2) and (3). `test_design_system.py` now asserts the strict check passes on a freshly set-up
module, so this cannot quietly return.

## The upgraded templates and the brandbook's colours — 2.88.0 (2026-11-03)

The owner approved, in the template gallery, a new body for every L61 template, six learning layouts and quick drills,
and ruled out flat line drawings as pictures (L67). This skill now owns:

- `templates/gb_layouts.css`, last block: Blue as the one accent, dark and photo slides on Navy (never Pitch Black),
  the NA pattern behind opening, task, check and summary slides and the start screen. `--lt-deep` is Navy.
- `templates/gb_upgrade.css`: the upgraded bodies (vocabulary §0b), every colour a token in its own `:root`, nothing
  tied to one slide's stop number. Made from the gallery's six proposal files; the flat-drawing animations of the
  three-blocks slide are left out (the live scene replaced them).
- `knowledge/design-system.json`: ships `gb_upgrade.css`, `gb_steps.js` (course-module-ux), `gb_scene.js`
  (course-visuals/scene) and the two pattern files.

The compiler loads `gb_upgrade.css` and `gb_steps.js` in every deck; neither changes a slide that does not use the new
markup. `design/slide-templates/` is the reference, built from these files only. `scripts/test_design_system.py` checks
the grounds, the pattern's places, that no rule names a stop number or a slide id, that no flat-drawing motion is left,
and that `gb_steps.js` is valid.

## The logo's gap — 2.84.1 (2026-11-02)

The owner: the logo was padded on the right but close to the top; it should be padded the same both ways. Measured on the
compiled slides at 1280 x 800, the artwork stood 64 px from the right edge and 14 px from the top. The official file
carries the brandbook's clear space inside its own box (X = 2/3 of the symbol's height: artwork x 143-757, y 142-606 of
900 x 747, symbol 214 units tall), and the box let that space run off the top of the slide, so the top was also under X
(about 26 px there).

`templates/gb_layouts.css` now places the artwork with one gap, `--lt-logo-gap: min(6vmin, 48px)`, from the top and the
right. Tried on the real slides at 1280 x 800 and 1024 x 768 first: 64 px both ways lines up with the slide margins but
brings the logo within about 14 px of a figure panel under it; 32 px moves it past the content edge and onto the photo
slide's full-screen button. The logo's size is unchanged. The photo slide's full-screen button (`gb_zoom.js`) moves from
the logo's corner to just under the artwork.

`course-factory/compile/scripts/test_compile_module.py` (L62 block) checks that the top and right both use the gap less
the file's own margin and that the gap is never under X at either classroom size; it fails on 2.84.0.

## Known gaps

1. **Not eval-tested.** No `evals/` directory, consistent with the rest of the family — and the
   same real gap the others record.
2. **Anatomy is deck-only — still open after the 2026-09-10 wiring.** The header band, card,
   zoom and takeaway specs come from decks. **Task screens and handouts have no visual anatomy
   here**, and `course-factory` step 8 therefore covers the deck's visual layer plus the shared
   token set only. Do not claim this skill defines a task or handout visual standard; it does
   not yet. Settling whether the measured task and handout palettes are intentional design or
   more drift (see *Deliberate omissions*) is the next piece of work.
3. **The `--warn` conflict is unresolved.** Across all 85 stylesheets `--warn` is `#B4453A`
   (a red) in 7 files and `#b8791a` (an orange) in 5. Those mean different things. The
   reference says red; the skill follows it, but the orange files were not investigated.
4. **No contrast verification of the token set itself.** The canonical pairs are recorded as
   used, not proven to pass WCAG AA on every ground they appear on. `course-module-ux` owns
   measurement; this skill hands it values. Someone should close that loop.
