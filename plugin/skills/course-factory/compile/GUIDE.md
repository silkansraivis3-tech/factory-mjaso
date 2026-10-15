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

## 2b · Real photographs, and no empty space (L52, L53 - owner, 2026-10-15)

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
- **Every drawing whole and clean (L54).** Also `audit_drawing.js`: no part pokes out of the hull, tank, room or box
  it sits in (draw the room along a sloping stern, or clip it), nothing is cut off at the drawing's frame, every label
  keeps 4 px clear of other shapes, lines and labels. A crossing that is meant is marked in the drawing:
  `data-may-cross`, `data-no-contain`, `data-may-overlap`. Every compiled deck also loads `gb_fit.js`, which widens a
  frame a drawing still reaches past and names it in the console - fix the drawing, then compile again.
- **Figures from the figure kit (L55).** `"s14": {"figure": "s14.kit.json", "dark": true}` - the spec lives in
  `working_claude\figures\M02\` like any drawing source. The compiler puts it into the page as data with the deck's own
  step buttons (`.mediabar`: previous, next, replay), and loads `kit.css` and `kit.js` (installed by `design_system.py`
  like `gb_deck.js`) and, when the course made parts of its own, `assets\kit_parts.js` after them. Each spec step lights
  its slide line (`"line": 2` -> `[data-i="2"]` `.cur`, earlier steps `.lit`); entering the slide starts the figure at
  step 0. Check the specs first: `course-visuals\kit\scripts\check_kit.py module <module> --figures <figures\M02>`.
- **A kit figure is laid out beside its words, and drawn to its panel (L53, operator 2026-10-15).** A figure whose
  steps light the slide's lines takes `"composition": "two-col"` (the words at reading size in the left column, each
  lit line a tap target for its step; `"boxes"` when the lines are separate items) - not `stage` with a `legend`, where a
  large drawing left the explanation in a row of small cards. Draw the spec to the panel's own shape (about 640 × 390 in
  the wide column, `scales()` in a deck reports the real scale), crop what the steps do not show, and run
  `audit_drawing.js` (its EMPTY check) at 1280 × 800, 1024 × 768 and 1920 × 1080, at step 0 and at the last step.
  `stage` stays for a figure that is the whole screen and has no lines to light.

- **Every photograph opens (L56) - nothing to ask for.** Every compiled deck loads `gb_photo.js`: a tap on any photo
  (the slide's picture, a split photo, an inset) opens it large with the slide's title, what it shows and its credit, and
  from there full screen; a full-screen photo slide gets a Photo button. The words come from the photo's `description` in
  `_photo_meta.json` - write it for the trainee when the photo comes in; a photo without one is reported at build.
  A generated picture (`"generated": true`, `"generator": "Nano Banana (...)"` in its record) is labelled "AI-generated
  illustration" in the panel, its credit and an inset's caption - never "Photo" - and is never an L57 thumbnail.
- **A drawing carries the real photos of what it shows (L57) - nothing to ask for.** The compiler takes the real things a
  drawn slide names - the term before " - " in its lines (with the kit figure's step number) and the drawing's own labels -
  and puts the matching photos in a row under the drawing (`.photo-strip`, at most four), each opening in the panel.
  Matched by `"shows"` in `_photo_meta.json`: give every photo the plain names of what it really shows, e.g.
  `"shows": ["bunkering station", "LNG bunker hose"]`. A photo of another module is copied in with `copied_from`; one
  awaiting a rights review is never used. Every real thing still without a photo is printed and written to
  `working_claude\PHOTOS_TO_TAKE.md` (the module's section is rewritten each build; `## Notes` is yours).
  Matching is by name only: when a matched photo contradicts how the thing is drawn (deck tanks under a drawing of a tank
  in its hold), say so in the build sheet - `"no_photo": ["fuel tank"]` with a `"_no_photo"` reason - and the thing goes
  on the list instead. Look at every thumbnail the build placed before showing the deck.
- **Every photograph once in the whole course (L58).** No photo is shown on two screens - in this module or any other;
  a copy under another name is the same photo (same `url_or_origin`, or the same bytes). A thumbnail takes a different
  photo or none; a photo you placed (picture, inset, photo in a drawing) that is already shown is reported - choose a
  different one or none (the earlier module keeps it). After photos change, build every module again.

## 2c · More build-sheet choices (2.25.3, proved on the pilot's Module 2)

| Key | What it does |
|---|---|
| `"legend": [2, 6]` | on a stage slide only lines 2-6 form the numbered row; the lines before go above the drawing, the rest below. Words that already start with their own number get no second badge |
| `"box_alt": [4]` | which boxes are amber (otherwise every second one) |
| `"groups": [{"lines": [2, 7], "class": "box z1"}]` | lines 2-7 in one box, the first as its bold heading (a zone with its list) |
| `"hooks": {"3": {"class": "m02-steptext", "data-step": "2"}}` | a figure script's handle on a line - a class word and `data-*`, never a look |
| `"inset": {..., "under": "figure"}` | the real photo goes under the drawing when the words fill their column |
| `"aside": "m02_s08_minis.html"` | small drawings that belong with the words |
| `"figure_first": true` | the drawing on the left, the words on the right |
| `"class": "m02-s3d"` | a hook for the module's drawing styles on the slide |

A room activity with a drawing of its own (trace a path) is laid out like a teaching slide and keeps the classroom's
Task marks. A task slide links to the existing page for its code (`tasks\sc2_*.html`) while task pages are not compiled.

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
