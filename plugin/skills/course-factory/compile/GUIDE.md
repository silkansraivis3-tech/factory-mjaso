# Building the deck from the approved script (2.25.0)

Read this lane when a module's script is approved and its presentation is made into its finished file
(built). **The words are typed
once — in the script.** `compile/scripts/compile_module.py` writes `modules\module01\presentation\index.html`
from it with the factory's own frame, style files and deck engine. Nobody edits that file by hand.
Why: `docs/PROPOSAL_SCRIPT_COMPILER.md`.

```
python compile/scripts/compile_module.py <course> --module 1 --init-build   once: a starter build sheet
python compile/scripts/compile_module.py <course> --module 1                build (again after every change)
python scripts/check_script_match.py <course> --module 1 --part instructor  the words are the approved ones
```

Then the usual checks: `check_navigation.py`, `check_course_package.py`, and in the browser the
`audit_deck.js`, `audit_collide.js` and `audit_compose.js` probes — the compiler does not prove a layout
fits, the audits do.

## 1 · What goes where

| File | Holds | Who changes it |
|---|---|---|
| `working_claude\script\M01.json` | the approved words — never touched by the compiler | the operator, through `content_script.py propose` → yes → `apply` |
| `working_claude\script\M01.build.json` | **how it is delivered**: each slide's picture file, a layout choice, a dark slide, the module's own drawing styles and figure scripts, the landing line, the footer title | the factory (Edit tool) — not content, so a change never undoes the approval |
| `working_claude\figures\M01\` | drawings as source: `.svg`, and `.html` fragments with their own markup | the factory, `course-visuals`, `image-director` |
| `modules\module01\assets\` | what ships: photographs (`img\`, credits in `_photo_meta.json`), style files, figure scripts | as today |

An `.html` drawing is never put in the module folder — the classroom would take it for a page and send it
to the tablets. Write a fragment as the deck sees it: its links start `../assets/`.

## 2 · How a slide is laid out — the same in every module

| In the script, or in the delivery file | On the screen |
|---|---|
| `layout` `visual_full` + a photograph | `.slide.photo` — the photo is the screen, the words over it |
| `layout` `split` | `two-col` — the words left, the picture right |
| `layout` `visual_wide` | `stage` when the words are short (45 or fewer), else `two-col wide-right` |
| `"composition"` in the build sheet | overrides: `opener`, `flow`, `two-col`, `wide-left`, `wide-right`, `stage` |
| a task slide | `activity` with its code, `data-task-href` to `tasks\sc1_<title>.html` / `assessment\check.html` |

The words: one line is a statement; several lines are a statement and its support list; a line starting
`• ` is a list item. Every line carries `data-i="1"`, `"2"` … so a figure that steps can light up its
own line: `document.querySelector('#s04 [data-i="2"]')`. A figure script registers its slide hooks as
`window.GB_HOOKS = window.GB_HOOKS || {}; GB_HOOKS.s05 = {enter: fn, leave: fn};`.

## 2b · Real photographs, and no empty space (L48, L49 - owner, 2026-10-15)

- **As many real photographs as possible.** A photograph as the slide's picture fills the screen (`visual_full`)
  or the right of it (`split`) - never a small photo in a column. Beside a drawing, add a real photo under the
  words: `"inset": {"photo": "assets/img/x.jpg", "caption": "On board: ..."}` (its credit is added for you).
- **Emphasis**, chosen per slide: `"boxes": [2, 3]` (two options, side by side in meaning), `"conclusion": 5`
  (the line the room must leave with), `"legend": true` (a stage drawing's lines as a numbered row). The term
  before " - " or ": " is set in bold automatically.
- **No empty space.** A drawing, animation or 3D model gets the wider column (`fig-wide`) and the column's
  height; words are at reading size (`.copy`). Before showing a deck: `audit_compose.js` (every screen composed,
  none weak), `audit_deck.js` (no spill, no overfill, no tiny labels), `audit_collide.js` - at 1280 × 800 and
  1024 × 768. A label inside a drawing below 12.5 px on screen is fixed in the drawing.
- **Every drawing whole and clean (L50).** Also `audit_drawing.js`: no part pokes out of the hull, tank, room or box
  it sits in (draw the room along a sloping stern, or clip it), nothing is cut off at the drawing's frame, every label
  keeps 4 px clear of other shapes, lines and labels. A crossing that is meant is marked in the drawing:
  `data-may-cross`, `data-no-contain`, `data-may-overlap`. Every compiled deck also loads `gb_fit.js`, which widens a
  frame a drawing still reaches past and names it in the console - fix the drawing, then compile again.

## 3 · When the look is not enough

If a slide needs something the shared style files cannot do, the answer is **never** a module style
file for text or layout — that is how modules stopped looking alike. Add it once to the shared files
(`course-module-ui`), so every module gets it on its next build. A module's own style file holds its
drawings' colours only.

## 4 · Safety

- Built only from an **approved** script; `--draft` gives a preview, marked as such, never handed over.
- A deck changed by hand — or built by hand before the compiler — is **not overwritten**; the change
  goes into the script or the build sheet, then `--force`.
- A missing picture is listed, never invented.
- The same script and build sheet always give the same file.

Not built yet: the task pages, the module check page and the start pages (next steps of the proposal).
