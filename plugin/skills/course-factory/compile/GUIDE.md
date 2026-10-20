# Building the deck from the approved script (2.25.0)

## Quickstart - one module, start to PASS (2.50.0). Read this; the rest of the file is reference.

```
1  python compile/scripts/compile_module.py <course> --module 1 --init-build
      the build sheet (working_claude\script\M01.build.json), a STARTER figure-kit spec for every drawn slide
      (working_claude\figures\M01\sNN.kit.json: the script's parts on a grid, a step per line) and the 3D starter entry -
      a 3D slide gets both (2.50.6): declining the 3D ("declined_3d") edits its 2D starter
2  read course-visuals\kit\CATALOGUE.md - one line per kit part, the spec format, marks and steps. Never kit.js.
3  fill the build sheet (each slide's picture, layout, the photos) and EDIT the starter specs - never write one from nothing
4  python compile/scripts/build_module.py <course> --module 1            again after every change, until PASS
      ONE command runs everything: every figure on its real slide at once (auto-fixes what has one right answer), the
      compile and its drawing check, the words (instructor + trainee), navigation, the audits at 1280x800 and 1024x768,
      the course pages and the classroom's importer. It prints only what fails - file, slide or question, what to do -
      and one PASS line. Do not run those checks one by one: each separate run is a turn of the model.
5  on PASS it has photographed every slide, every figure step and every question (asked, wrong, right) onto a few
      sheets and checked that every question grades right and wrong answers as such. Give the sheets to ONE review
      subagent (model haiku) with compile/REVIEW_PROMPT.md. It labels each finding BROKEN or POLISH (2.56.0). Fix every
      BROKEN one in one go, build again, and send the same reviewer a re-review (the changed screens only, with its
      BROKEN list: FIXED / NOT FIXED - no new polish). POLISH is never fixed in the loop: write it to
      working_claude\review\MNN\POLISH.md for the operator - a fix to a drawing that already passes can break it again
      (IGF M02 s02: PASS, then four failed builds). Every BROKEN finding is fixed before hand-over, so the loop ends (M01
      benchmark: 6 open-ended review passes took 18 of 29 minutes).
   A FIGURE problem (from the build or the review): fix it in the studio, not in build after build -
      course-visuals\kit\scripts\studio.py <spec> --step all judges one figure at every step in seconds, on its real
      slide or task page (2.52.1). The build lists each finding's spec part ("[part TK1]") and those parts' numbers
      together: change them together, try in the studio until clean, then ONE build_module.py run. While only figures
      fail, build_module.py stops after them (a figures-only round, ~1 min) and runs the rest once they are clean. (Proved on the IGF M01 round-1 build: haiku found both problems the old browser-driving
      review found - the q03 tap area on the mast's cap only, a leader line through a caption - in 3 calls, $0.02,
      where the old review took 100 calls and $2.42.)
```

- **A figure problem** is reported once per figure and part, with the step. `figure_fit.py` has already tried the fixes
  with one right answer: a drawing lost in empty space is cropped to what it shows; a drawing whose column got narrower
  (a layout changed) is re-fitted to it. Kept only when every audit is clean (figures\M01\_fit\ - the spec is never
  rewritten). When it gets close but not clean, it saves the attempt as `_fit\sNN.sNN.candidate.kit.json`: copy it over
  the spec and fix what it lists. To look at one figure at every step: `course-visuals\kit\scripts\studio.py <spec>
  --step all`.
- **Effort.** The mechanical loop - build, read the failure, change a number in a spec or a key in the build sheet, build
  again - needs no deep thinking: it can run at medium effort. Keep high effort for the design decisions: which picture
  teaches the slide, what a figure shows, 3D or not, what the operator must be asked.
- **A parallel build** (one agent per module): add `--no-course-pages` - one process writes COURSE.html (§5).
- **A revision** (operator corrections): words through `content_script.py propose` -> `apply`; layout and figure changes
  in the build sheet and specs; then step 4 once.

Read this lane when a module's script is approved and its presentation is made into its finished file
(built). **The words are typed
once — in the script.** `compile/scripts/compile_module.py` writes `modules\module01\presentation\index.html`
from it with the factory's own frame, style files and deck engine. Nobody edits that file by hand.
Why: `docs/PROPOSAL_SCRIPT_COMPILER.md`.

```
python compile/scripts/compile_module.py <course> --module 1 --init-build   once: a starter build sheet (2.49.1: landing
                                                                            rule, pass mark from the course's other sheets; a foot;
                                                                            an entry per tap / label question)
python compile/scripts/compile_module.py <course> --module 1                build (again after every change)
python scripts/check_script_match.py <course> --module 1 --part instructor  the words are the approved ones
```

**The module's design files (2.49.2).** Both `--init-build` and every compile first check the module's design files
(style files, engines, `kit.js` ...) against the factory's with `design_system.py`'s own check, and **say what they did**,
on the first line: *all N are the factory's own - nothing changed*; or *Design files were missing in ... - installed the
factory's N*; or *N were not the factory's current ones - updated from the factory: kit.js (older version) ...* (files
that only fell behind are put right, so a build never runs on an old `kit.js`). A file **edited inside the module** is
different: the build stops (exit 2, nothing built), names the file and gives the exact `design_system.py install <module>
--update` command (or, if the operator chose the different look, `design_choices.py add ... --rule shared-design`).
**`--module final`** builds into the folder after the last planned module (architecture.json's modules + 1 - IGF: 15
planned, so `module16`); with no architecture to count in, give `--module-dir`.
**A final with two variants** (FA, FB) is two graded pages: `assessment\final_a.html`, `assessment\final_b.html`
(PASSED / NOT PASSED, the pass mark, one answer-key section each; the deck's slides are Check slides, the landing card
and the start page say "Final assessment A / B"). A single variant stays `assessment\final.html`.
**A draft** (`--draft`, script not approved) writes `DRAFT_NOT_PACKAGED.txt` into the module folder: its preview stays
viewable where its assets are, but `compile_course.py` and `check_course_package.py` leave it out - COURSE.html, the
module list, every check and the importer's run - and say `moduleNN: draft - not packaged`. Building the approved script
removes the mark.

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

**Every slide is one of the owner's thirteen layout templates (L61, 2.52.0).** The compiler chooses it from the rows
below and names it on the slide: `data-template="explain-figure.v1"` `data-variant="figure-right"`
(`course-module-ui/knowledge/layout-templates.json`). `gb_layouts.css` gives it the owner's look in the brandbook's
colours, the official logo top right, Raleway bundled. What the compiler chooses on its own:

| The slide | Its template |
|---|---|
| a photograph full screen / beside the words / in its own column | `photo-explain` `full` / `split` / `column` |
| a drawing on a stage | `figure-stage` |
| a picture beside up to 60 words | `explain-figure` `figure-right` (`figure-left` with `"figure_first"`) |
| a picture beside more than 60 words | `reading-with-figure` - or `long-explanation` when the picture is 3D |
| a picture beside more than 135 words | `content-in-parts`: the lines in order, in parts of about 110 words; Next walks the parts, every part has a tab |
| lines numbered 1, 2, 3 ... | `procedure` (`with-figure`, or `text-only`) |
| lines whose cells are separated by ` \| ` | `reference-table` - one row a line, the separator kept in the line (hidden) |
| a short slide with no picture | `explain-figure` `text-only` |
| the opener / the recap / a task slide or room activity | `opening` / `recap` / `task-launch` (`tablet`, `check`, `room`) |

Asked for by name in the build sheet: `"template"` (any of the thirteen; `compare-two` needs `"blocks": [[1, 2], [3, 4]]`
and `"figure_b"`, `three-content-blocks` needs three `"blocks"`), `"variant"`, `"split": 0.5`-`0.6` (the text's share),
`"parts": [[1, 4], [5, 9]]`, `"panel": "light"` (a drawing made for a white page; the panel is Navy otherwise). An
unknown or unsuitable template or variant is a problem with the slide's id.

**The owner's rules, checked at every build:** a split slide is 55 / 45 (50-60 % text, never 80 / 20); more than 60
words always has a picture beside it; never three teaching slides in a row without a teaching picture (a task launch and
the recap neither count nor break the run); approved words are never cut, summarised or set smaller - when they need
more room they go into parts. A drawing is now about 45 % of the slide wide, not 60 %: one whose labels become too
small at that width is reported by the drawing check like any other - give it bigger labels, `"split": 0.5`, or the
`figure-stage` template.

| In the script, or in the delivery file | On the screen |
|---|---|
| `layout` `visual_full` + a photograph | `.slide.photo` — the photo is the screen, the words over it; past 45 words (2.52.0) the photo beside the words (`two-col`, the split photo) - set by itself, no build-sheet choice |
| `layout` `split` | `two-col` — the words left, the picture right |
| `layout` `visual_wide` | `stage` when the words are short (45 or fewer), else `two-col wide-right` |
| `"composition"` in the build sheet | overrides: `opener`, `flow`, `two-col`, `wide-left`, `wide-right`, `stage` |
| a photograph + `two-col` | the photo fills the right of the screen, the words on a dark scrim (`photo split`, fixed width) |
| a photograph + `wide-left` / `wide-right` (2.49.1) | a real column layout: the words as wide as the layout says, the photo cropped to fill its own column, its credit line on the slide. Use it when the words do not fit beside a `photo split` (IGF M06 s10 spilled 14 px) |
| a photograph inside a figure fragment (2.49.1) | keeps the slide's visible credit line (the photo's, unless the build sheet's `"credit"` says otherwise, or the fragment's own caption already has it) |
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
- **Draw a kit figure in the studio, not in the compile (2.48.0).** `course-visuals\kit\scripts\studio.py
  working_claude\figures\M03\s07.kit.json` draws the spec on its real slide (the script's words, the build sheet's
  layout, the module's styles) at 1280 × 800 and 1024 × 768, runs every drawing audit at the end of every step, and saves
  a screenshot - in seconds. Change the spec until it is clean, then compile once. The kit does the drawing work by
  itself: every label gets a clear place (a leader line if it had to move), no word is drawn under 12.5 px, boxes are as
  wide as their words, the frame grows or zooms to hold and fill, and the colours follow the panel (dark deck, light task
  page). A spec never places a label; a `"text"` with `"to": [x, y]` is a callout joined to that place.
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
  **Not a thing (2.49.1).** The words a chart draws - an axis, a line, a zone ("Air line") - are no real thing: a figure
  made only of the kit's chart parts (`scale`, `bands`, `curve_chart`, `flammability`, `range_bar`, bare `text`) is
  skipped. For any other name that is no thing, `"not_things": ["air line"]` (with a `"_not_things"` reason) takes it
  off the list altogether - `"no_photo"` keeps it listed.
- **A planned photo that does not exist (2.49.0).** The build names every photo slide with no picture file. Find the
  real one first (project, factory library, a free licence - `course-visuals`). If none exists and the slide only sets
  the scene, propose an AI picture unasked - `nano-banana:realistic-visuals`: describe it, show the prompt and the
  price, make it only after the person's yes, record it `"generated": true` in `_photo_meta.json`. Equipment a trainee
  must recognise is never an AI picture (L33): it stays a photo to take.
- **A `model_3d` slide (2.49.0, L46).** The scene is the module's own three.js file, listed in the build sheet's
  scripts like M03's `m03_station3d.js`, built to `knowledge/media-and-tasks.json` → `three_d.performance` (one shared
  renderer, built with its slide, first frame within 1 s and 30 fps with the CPU slowed 4x).
  **Build the scene on the slide BEFORE it (2.49.2).** The first frame under 1 s is only reachable when the scene is
  already built - geometry, materials, first render - while the trainees are still looking at the slide before: hook
  the slide before's entry in `window.GB_HOOKS` to build it (hidden), and the 3D slide's own hook only reveals the
  canvas and draws; honour `window.__noPrepare` and report `window.__scene3d` as `measure/GUIDE.md` §2b says - the
  measuring tool reads it. A scene built when its slide opens took seconds on the throttled CPU in IGF M07-M15. **Measure it**: `node course-module-ux/measure/scripts/perf3d.mjs <deck.html>
  --slides=all` (Node + headless Chrome, CPU slowed 4x, warm and cold first frame, fps; exit 1 over budget; see
  `measure/GUIDE.md` §2b). **Every 3D scene answers a tap** (`three_d.interaction`): a tap - not a drag - on a part
  highlights it (blue glow, the camera frames it, its name shows); a second tap on it, or a tap beside the parts,
  puts the view back. The parts that can be tapped are the ones the labels name; raycast only on the tap, never per
  frame; buttons and taps share one mode. Reference: IGF M03 `m03_station3d.js` (the highlight, the tap logic on
  `pointerup`). A scene that only turns is not finished. A `[data-stage]` in a wide column takes the column's own
  height (2.49.2) - no module override needed.
  **At least one scene per module where the subject allows it - strongly recommended (L60, 2.49.7).** `--init-build`
  gives a `model_3d` slide a starter scene entry: its figure (`m01_s05_3d.html`), its scene file and `three.min.js` in
  `"scripts"`, and a `"_figure"` note on how to build it - the build reports the files missing until they are written.
  It also writes the slide's 2D starter spec (`sNN.kit.json`, 2.50.6), named in the entry's `"_2d"` note but not in
  `"figure"`: to keep a 2D figure, point `"figure"` at it, take the scene files off `"scripts"` and write
  `"declined_3d"` - then edit the starter, never write a spec from nothing (M01 benchmark run 5, s05).
  A script with no `model_3d` slide gets the same entry on its best slide, unasked (`content_script.best_3d`: a shape,
  an inside or a layout in space; never a real photo's slide), with a `"_3d"` note saying why. A module built with no
  scene gets a RECOMMENDED block in the build and its own card on the review page, naming the best candidate - never a
  block: the operator declines with their reason, `"declined_3d"` at the TOP of the build sheet, and it is not
  proposed again. A 3D slide whose
  figure is not a scene (a kit figure, an `.svg`, a photo - anything but an `.html` figure holding a `[data-stage]`,
  `data-3d`, `data-scene` or a `<canvas>`) is a must-fix in the build and a note on the script's review page:
  "asks for a 3D scene; it has a 2D figure". To keep the 2D figure, write the operator's reason in the slide's entry,
  `"declined_3d": "<their reason>"`; it is not flagged again. The deck's `data-visual` and the plan then say the 2D
  kind it was built with (2.52.0), and a cue line that still asks to rotate, zoom, cut open, drag or "tap each part"
  of a picture that cannot is a must-fix, with a drafted line in `working_claude\script\MNN.cue_fixes.json` and the
  `content_script.py propose` command that shows it to the operator; or keep it with `"cue_kept": "<their reason>"`.
- **Only what a page shows ships (2.52.0).** After each build a picture of `assets\img\` that no built page names goes,
  with its record, to `assets\img\_unused\` (skipped by the classroom); name it in the build sheet again and it comes
  back. `used_in` in `_photo_meta.json` is written by the build. A tap / spot / label / read-the-instrument question whose
  subject a real photo of the module shows is listed after the build with the build-sheet line - a note.
- **Every photograph once in the whole course (L58).** No photo is shown on two screens - in this module or any other;
  a copy under another name is the same photo (same `url_or_origin`, or the same bytes). A thumbnail takes a different
  photo or none; a photo you placed (picture, inset, photo in a drawing) that is already shown is reported - choose a
  different one or none (the earlier module keeps it). After photos change, build every module again.

## 2c · More build-sheet choices (2.25.3, proved on the pilot's Module 2)

| Key | What it does |
|---|---|
| `"legend": [2, 6]` | on a stage slide only lines 2-6 form the numbered row; the lines before go above the drawing, the rest below. Words that already start with their own number get no second badge |
| `"box_alt": [4]` | which boxes are grey - the other of two options side by side. Without it every box is blue: amber is only ever the line a stepping figure is on (2.49.6) |
| `"groups": [{"lines": [2, 7], "class": "box z1"}]` | lines 2-7 in one box, the first as its bold heading (a zone with its list) |
| `"hooks": {"3": {"class": "m02-steptext", "data-step": "2"}}` | a figure script's handle on a line - a class word and `data-*`, never a look |
| `"inset": {..., "under": "figure"}` | the real photo goes under the drawing when the words fill their column. It takes ~220 px of the drawing's panel: when that leaves the drawing under ~60 % (a 640 x 390 spec keeps 47 %), the build says so (2.49.1) - put the inset under the words, use `"over"`, or draw the figure wider and less tall |
| `"inset": {..., "over": {"x": 140, "y": 8, "w": 176}}` | the photo lies on a blank part of a kit drawing, in the drawing's units - the drawing keeps the whole column and its full size (a photo under a drawing squeezed it to half size, its labels to 7 px). It still opens full screen; look at it at every step, the drawing check does not see what a photo covers |
| `"aside": "m02_s08_minis.html"` | small drawings that belong with the words |
| `"figure_first": true` | the drawing on the left, the words on the right |
| `"class": "m02-s3d"` | a hook for the module's drawing styles on the slide |

A room activity with a drawing of its own (trace a path) is laid out like a teaching slide and keeps the classroom's
Task marks. A task slide links to its set's page (`tasks\sc2_*.html`, `assessment\check.html`) - built by §2d.

## 2d · The task pages (2.34.0)

Every task slide that opens questions gets its page from the same script: `tasks\sc1_<title>.html`,
`assessment\check.html`, `assessment\final.html` (`final_a.html`, `final_b.html` for a final with variants, 2.49.2). A
real photograph beside a question carries its credit as a line on the picture and the round ⤢ button that opens it full
screen, as on a slide; a control with ready / pressed positions on an operate-the-panel card is drawn with the kit's
`push_button`. The page is only its questions as markup; how a trainee answers,
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
- **A real photograph, or a figure-kit drawing, instead of an .svg (2.43.0).** The same `"figure"` may be
  `"assets/img/pump_room.jpg"` (a photo in the module's `assets/img` with its record in `_photo_meta.json` - use as many
  real photographs as possible: tap the place, spot the hazard, read the instrument, label the drawing) or
  `"m04_chart.kit.json"` (the deck's own kit spec, drawn still at its last step - never copy a kit chart into an SVG).
  A photograph has no drawing to find places on, so each answer's place is its box in % of the photograph:
  `"areas": {"Relief valve": [62.5, 31, 12, 18]}`; a missing file, record, credit or box is reported, an image-model
  picture is refused. A tap on it stays the answer - it opens full screen by its corner button. A kit drawing's places are
  its part ids or the words a part is drawn with (`"areas": {"Fuel tank": "ft"}`) - and a place drawn inside a part:
  a side-view ga's funnel and house, `"areas": {"Funnel": "G.funnel"}` (2.52.0; never a % box); `"kit_step": 2` (or a word of a step's
  title) shows another step; **`"unlabel": "answers"`** (2.49.1, the choice to make) takes the words off only the parts
  the answers name (`areas` / `labels`) and their callouts - a `text` part pointing at them (`"to": [x, y]` inside the
  part), one with `"for": "<part id>"`, or one whose id is `T_<part id>` - so the rest of the drawing keeps its words and
  does not read blank. `"unlabel": "all"` also takes every free `text` part and the deck's context words (IGF M06 q08
  came out 51 % blank), and `["P1"]` takes exactly those ids. With `"answers"` or a list the words are laid out with the
  rest and then hidden (the spec's `"ghost"`, 2.50.4), so the words left stand where the deck has them - taking them out
  re-laid the rest and put a label beside the wrong space (M01 benchmark run 4). The same `"figure"` also puts a picture beside a single /
  multi choice, above match, categorise, order, cloze, scenario ..., and `"figures": {"Plan A": "assets/img/a.jpg"}` over
  a `compare` column. With a picture beside four choices - or beside the cards of a sort, an order or a match (2.49.1) -
  the compiler lays them side by side on a landscape tablet, so no choice and no drop zone is ever under the Check bar.
  A task photograph's `alt` is the build sheet's `"alt"`, else the question's `visual`, else the photo record's description
  (name / about / shows): write `"alt"` when the description would give the answer away.
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
  covers what is drawn, with a leader line to each place. Every box is as wide as the longest label needs, in two lines,
  with room for the tick (2.46.0), and placed by itself (`label_layout.py`, 2.48.0): each as close to its place as the
  others allow, in the same order, never off the edge, onto another or under the ⤢ button. Leave `"box"` out - IGF M01,
  M02 and M03 no longer need theirs; `"labels": {"Fuel tank": {"at": "sp-tank"}}` only names the place. A `"box"` given
  there still wins, and one too narrow for its words is reported. **Boxes that do not fit two rows as wide as the
  drawing** (2.50.6): a drawing shown narrower than the screen - a 2:1 drawing under its bands is as tall as it may be and
  only ~560 of the row's 1240 px wide - gets rows that reach past it on both sides, as far as the drawing keeps its size
  (`task_pages.label_side`); five two-line labels then fit three below and two above (M01 benchmark run 5's m01 placed
  all five by hand). Only what not even the screen's width holds is reported.
- **The page:** the course's first self-check opens with "try your tablet first" (`"try_tablet": false` on the task
  slide's entry to leave it out); a check opens with its pass mark - the approved script's `"pass_mark"` (2.46.0,
  corrected like any other word: `content_script.py propose` with `{"script_field": "pass_mark", "new": 80}`), else
  `"pass_mark": 70` at the top of the build sheet; both, and different, is reported.
- **The instructor's answer key** (2.46.0): `assessment\check_answer_key.html` is compiled with the task pages from the
  same approved script - every question of every set in order, how it is answered, the right answer in the script's
  words (the letters the tablet shows, the order, the gap's words, the dial's accepted values), the feedback, and how
  the pages mark with the pass mark. Instructor-only by its name; `compile_course.py` lists it on START_HERE_EXTENDED.
  No key is typed by hand any more - IGF M01-M03's were retired because they held answers corrected since.
- **The instructor's plan** (2.47.0): `instructor\M01_PLAN.html` is compiled with the deck and the task pages
  (`--only plan` builds it alone) - allocated against built minutes on its face (a mismatch is shown and reported), the
  Main ILO and Sub-ILOs with where each is taught and checked, every screen with its minute and the script's notes, every
  task set with its pass mark and questions, the room activities with their link hints, the equipment and the sources.
  Never typed: correct the script and compile again. A plan changed by hand (or made before the compiler) is kept until
  `--force`.
- **Layouts the engine picks by itself** (2.46.0): a drawing to tap that is not wide (width / height < 1.8) takes the
  screen's height with the explanation beside it; a list of 6 or more to order, build, match or rebuild has its
  numbered places beside the cards; a task slide in the deck shows the gesture its set mostly asks for (choose, tap,
  drag, order, dial, find, gap) instead of one tablet icon.
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
- **A drawing that moves is judged on every frame (2.50.6).** A running engine's pistons, a cylinder's piston, a vent's
  puffs, a flow: the check holds every endless animation still at 9 moments of one clock and reports what goes wrong on
  any of them ("on 1 of 9 frames of its motion"), so an unchanged spec gets the same verdict at every build (M01 benchmark
  run 5: s03 flipped between PASS and FAIL). The kit lays its labels out clear of what a moving part sweeps, the `engine`
  keeps RUNNING clear of its pistons' whole stroke, and a `vent`'s puffs rise only into free air (2.50.7). A finding on
  a moving part is the spec's to fix; for puffs the build says how ("fix (vent)": lower the outlet - run 5's s03 passed
  with its vent at y 230 instead of 196, 8 units under the other ship's keel).
- The screen's own words (Check, Next, Your score ...) are English for now; another course language is reported.

## 2f · The visual review - required (2.44.0, build-order step 16)

Every automatic probe was green on IGF Module 4 while a look at the screens still found invisible curves, a credit
showing an internal file path, a broken "choose all" and tap areas off the things they name. The probes measure what
someone thought to measure; only looking finds the rest. So **looking is a required step**, not a courtesy:

- **Who:** ONE review subagent, model `haiku` or `sonnet` (the main session never views the pictures; it gets a short
  verdict). Its brief is `compile/REVIEW_PROMPT.md`. It reads sheets; it never drives a browser (2.50.0 - the M01
  benchmark's browser-driving review took 100 model calls and a third of the module's cost).
- **What:** a screenshot of **every slide** of the deck, **every step** of a figure that steps, and **every question**
  of every task page and the module check - as asked (every tap area and drop zone outlined by a review overlay), answered
  wrong and checked, answered right and checked - at **1280 × 800**. Not a sample. `build_module.py` makes them on a pass
  (`course-module-ux/measure/scripts/review_sheets.mjs <module> <out>`, two screens to a sheet, in
  `working_claude\review\M01\`); the next review gets only the screens whose picture changed (`--all` for every one).
  Item 4 below is checked by the script: each question is answered by its own keys, and a right answer not graded right
  (or a wrong one graded right) fails the build.
- **Against this list:**
  1. every curve, line and label is visible against what is behind it (a kit figure sits on a dark panel - nothing navy
     or steel on it, nothing hidden under a shape);
  2. every credit and caption is clean - no file path, no drive letter, no internal folder name;
  3. every tap area sits on the thing it names; every drawn label is beside what it labels;
  4. every answer type is answered **once right and once wrong**, and the screen says which it was ("choose all" keeps
     every tapped option and scores a fully right answer as right);
  5. nothing is cut off, covered, or sits under the Check bar until the page is scrolled.
- **After:** fix what it found, build again, review the screens that changed. `compile_module.py` prints this under
  **Next** after every clean build. A module is not handed over until it is done.
- **Two backstops that are cheap and automatic** (they do not replace the review): the drawing check (§2e) now also
  reports a part of a kit figure that cannot be seen on the figure's dark panel (`contrast`: a label under 4.5:1, a
  shape or line under 3:1; the kit's own parts are exempt; `data-low-contrast` marks a part meant to be quiet), and a
  credit, caption or full-screen record that shows a file-system path or a drive letter is a **build problem**.

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
- An inset photograph under more than about 75 words (90 on a photo split) is reported at build with the px it will
  spill (IGF M07 s08 / s12, M09 s06: 79-105 px at 91-101 words) - before the drawing check finds it. Cut the words,
  put the photograph on a task question, or lay it "over" a blank part of a kit drawing.
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

**Languages (2.40.0, L19; the deck 2.41.0).** The words the factory itself puts on a task page (`task_pages.py` WORDS,
the engine's in `gb_answer.js`), on the deck (the deck engine's in `gb_deck.js` LANG, the landing card's in
`compile_module.py` LANDING) and on the start pages (`compile_course.py` WORDS) exist in English, Latvian and Russian, chosen by
the script's / architecture's `course_language` - the whole page in one language, `<html lang>` set to its code
("Latvian" is lv, never "la"). The lv and ru words are **PROVISIONAL** until a native speaker has checked them:
`compile/TRANSLATIONS_REVIEW.md` lists every one. Any other language is reported (exit 1) and the factory's words
on that page are English - never silently. A task page's file name is its title in plain letters (Vārsti → varsti,
клапаны → klapany). The owner's ruling of 2026-09-30 stands: every Novikontas course is in English unless one is
explicitly made in another language.
