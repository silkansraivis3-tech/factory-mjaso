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
