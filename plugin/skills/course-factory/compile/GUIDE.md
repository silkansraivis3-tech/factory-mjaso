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

When the modules are built - and again whenever one is added or its tasks change - the course's own pages, once
for the whole course, by one process (never a module agent: §5):

```
python compile/scripts/compile_course.py <course>                 COURSE.html, _course_shell\course_map.js, every module's start pages
python scripts/check_course_package.py <course>\modules           the classroom's own importer
```

Then the usual checks: `check_navigation.py`, `check_course_package.py`, and in the browser the
`audit_deck.js`, `audit_collide.js` and `audit_compose.js` probes — the compiler does not prove a layout
fits, the audits do. The drawing check (`audit_drawing.js`) is the one the build runs itself (§2e).

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

- **Every picture opens full screen, a photo with what it shows (L51, L56) - nothing to ask for.** Every compiled deck
  loads L51's one viewer, `gb_zoom.js`: a tap on any picture opens it full screen (pinch / + / − to look closer); a
  photograph's record - what it shows and its credit - stands under it, written by the compiler from the photo's
  `description` in `_photo_meta.json` (write it for the trainee when the photo comes in; a photo without one is reported
  at build). A full-screen photo slide opens on a tap of its bare picture and has the ⤢ button. A generated picture
  (`"generated": true` in its record) gets no credit line and no label on screen, and is never an L57 thumbnail.
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
| `"inset": {..., "over": {"x": 140, "y": 8, "w": 176}}` | the photo lies on a blank part of a kit drawing, in the drawing's units - the drawing keeps the whole column and its full size (a photo under a drawing squeezed it to half size, its labels to 7 px). It still opens full screen; look at it at every step, the drawing check does not see what a photo covers |
| `"aside": "m02_s08_minis.html"` | small drawings that belong with the words |
| `"figure_first": true` | the drawing on the left, the words on the right |
| `"class": "m02-s3d"` | a hook for the module's drawing styles on the slide |

A room activity with a drawing of its own (trace a path) is laid out like a teaching slide and keeps the classroom's
Task marks. A task slide links to its set's page (`tasks\sc2_*.html`, `assessment\check.html`) - built by §2d.

## 2d · The task pages (2.34.0)

Every task slide that opens questions gets its page from the same script: `tasks\sc1_<title>.html`,
`assessment\check.html`, `assessment\final.html`. The page is only its questions as markup; how a trainee answers,
grading by `data-key`, the result ring, PASSED / NOT PASSED and the classroom messages (`gb-task-done`, `gb-timer`)
are the factory's one shared engine, `gb_answer.js` + `gb_answer.css` (course-task-ux/assets, installed by
`design_system.py` like `gb_deck.js`) - promoted from the IGF pilot's Module 1. `--only tasks` builds only these.

- **Built: all nineteen ways of answering** an approved script can hold (2.38.0) - single_choice, multi_select,
  read_instrument, hotspot, spot_the_hazard, match, categorise, label_diagram, order, and cloze, choose_and_justify,
  scenario, set_value, find_the_fault, spot_the_error, build_the_plan, timeline, compare, panel_operate. No trainee
  task page is made by hand any more; the one engine grades them all, tap and drag only (L38, L42).
- **On a picture** (hotspot, spot_the_hazard, label_diagram, read_instrument) the build sheet names the drawing, keyed
  by the question's id: `"q01": {"figure": "assets/fig/m01_ga.svg"}`. Each answer's place is found by itself - the
  drawing's element with `data-name` equal to the answer's words, and in it the shape of class `hit` (rect, circle,
  or a path of straight lines; a group's `translate()` is followed), grown to a 56 px tap target. What the drawing
  does not name gets a box: `"areas": {"Funnel": [left, top, width, height]}` in % of the drawing, or the id of its
  element: `"areas": {"Accommodation": "hs-acc"}` - never guessed. The drawing's own labels (`#labels`,
  `[data-task-hide]`) are hidden.
- **Beside a picture** (set_value, find_the_fault, panel_operate) a drawing is optional: `"figure"` shows it above
  the task. **Set the value** is a dial from the range's low to its high end; its step is the tolerance when the value
  falls on it, else the largest round step under it that does (or `"step": 0.5`); one key per accepted step. **Operate
  the panel** shows every position a control can take: the opposite of the one it must end in (open / closed,
  running / stopped, on / off, auto / manual ... in en, lv and ru), or `"states": {"Purge mode": ["Off", "Sweep",
  "Hold"]}`; a control may start in a position: `"start": {"Vent fan": "stopped"}`. A valve or a pump is drawn by the
  figure kit and follows the position chosen. A control whose positions are not known is reported, never guessed.
- **Two-part questions** - a scenario's steps, the incident's order and then its stop point - have a Check for each
  part; the question is right when every part is.
- **A team task** (2.39.0) - a task slide with `"team": {"size", "roles", "scope"}` in the script - is marked on the
  slide (`data-mode="team"`, `data-team-size`, `data-roles`) and on its page (`task-mode`, `task-roles`, `task-scope`
  metas), per `classroom-system.json` `team_task`. The engine shows the team's name and the trainee's role at the
  top when the classroom sends `gb-team`, and runs as an individual task when none comes. Scope `team`: the first
  tablet of the team to finish hands in the one answer with `scope: 'team'`; the others show "Handed in by ... for
  Team A" when the classroom says so (`gb-team-done`). Scope `member`: everyone answers. Any team size; a role
  never locks anyone out of the task.
- **Label the drawing:** the compiler adds a band above and below the drawing for the empty label boxes, so no box
  covers what is drawn, with a leader line to each place. Or place them yourself: `"labels": {"Fuel tank": {"at":
  "sp-tank", "box": [left, top, width]}}`.
- **The page:** the course's first self-check opens with "try your tablet first" (`"try_tablet": false` on the task
  slide's entry to leave it out); a check opens with its pass mark (`"pass_mark": 70` at the top of the build sheet).
- **Before showing it:** `check_script_match.py --part trainee` and `check_course_package.py`. The drawings are
  checked by the build itself (§2e), question by question - a drawing shared with the deck is checked again here,
  without its labels and at task size.

## 2e · Every drawing checked at every build (L54, 2.35.0)

Nothing poking out, nothing cut off, no crowded label, no drawing lost in empty space - **anywhere**, and not left to
memory: after writing its pages `compile_module.py` opens each in a hidden Chrome or Edge at 1280 × 800 and runs
`audit_drawing.js` on it (`drawing_check.py`) - the deck slide by slide, a task page question by question. Every
finding is a problem to fix before the module is shown (exit 1), named by page, slide or question and part. A crossing
that is meant is marked in the drawing (`data-may-cross`, `data-no-contain`, `data-may-overlap`), so the reason is
written down. No Chrome or Edge: the build says it did not check. `--no-drawing-check` only while working on a drawing.
`drawing_check.py <page.html> ...` checks any page by hand - a hand-built one too.
- The screen's own words (Check, Next, Your score ...) are English for now; another course language is reported.

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

## 5 · The course's own pages (2.37.0)

`compile_course.py` writes what classroom-system.json says the factory writes and no script did before - all of it
from what is already approved and built, nothing new:

| Page | From |
|---|---|
| `modules\COURSE.html` — `<title>` = the course ID in the classroom; a `description` its importer quotes | `architecture.json` `course.title`; `programme.json` hours; `working_claude\course.build.json` `"regulation"`, `"programme"` (how the course is named — delivery, like a build sheet) |
| `modules\_course_shell\course_map.js` — the module order and titles, as data | the module folders; each title from its approved script |
| `moduleNN\START_HERE.html` — opens the deck at once | the script's title |
| `moduleNN\START_HERE_EXTENDED.html` — the deck, every task page, the instructor's files | the built deck's task slides (`data-activity`, `data-task-href`); `instructor\*.html`, `*answer_key*.html`, `handout\` as they are in the folder |

- **The course title never changes by itself.** It is recorded at the first build; a new title in the architecture,
  or a hand-made `COURSE.html` with another one, stops the build — a new title is a new course in the classroom.
  `--retitle` only when the course was never added there.
- A planned module not built yet is named on the course page ("Modules 4 to 16 are added as each one is approved"),
  never listed.
- A task slide whose page is not in the module folder is reported — build the task pages first.
- Generated, like the deck: a page changed by hand is not overwritten without `--force`; the same input gives the
  same bytes. `course.json` is **not** written: the classroom's importer makes it from these two files.
- `COURSE.html` wears the shared look: `gb_tokens.css` and `gb_page.css` are copied into `_course_shell\`.
- A module agent never runs it: two agents writing `COURSE.html` is a lost write no test catches
  (`orchestration/GUIDE.md` Rule 3).

**Languages (2.40.0, L19).** The words the factory itself puts on a task page (`task_pages.py` WORDS, the engine's in
`gb_answer.js`) and on the start pages (`compile_course.py` WORDS) exist in English, Latvian and Russian, chosen by
the script's / architecture's `course_language` - the whole page in one language, `<html lang>` set to its code
("Latvian" is lv, never "la"). The lv and ru words are **PROVISIONAL** until a native speaker has checked them:
`compile/TRANSLATIONS_REVIEW.md` lists every one. Any other language is reported (exit 1) and the factory's words
on that page are English - never silently. A task page's file name is its title in plain letters (Vārsti → varsti,
клапаны → klapany). The owner's ruling of 2026-09-30 stands: every Novikontas course is in English unless one is
explicitly made in another language.
