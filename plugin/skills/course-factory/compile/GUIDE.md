# Building the deck from the approved script

## Quickstart - one module, start to PASS. Read this; the rest of the file is reference.

```
0  PHASE A needs no agent: compile/scripts/phase_a.py <course> --modules 1-21 does steps 1 and 4 for every module in one
      local queue (and --auto: each photo slot whose course-catalogue pick is good takes it). A module it leaves at
      PHASE A CLEAN (exit 4) has only its pictures left: PHASE B reads working_claude\visuals\M01_VISUAL_NEEDS.md (each
      slot's kind, shape, px size, words, candidates) and CATALOGUE.md - nothing else - fills them, and runs step 4 once.
1  python compile/scripts/compile_module.py <course> --module 1 --init-build
      the build sheet (working_claude\script\M01.build.json), a STARTER figure-kit spec for every drawn slide
      (working_claude\figures\M01\sNN.kit.json: the script's parts on a grid, a step per line), the 3D starter (sNN.kit3d.json,
      SPEC.md; declining it - "declined_3d" - edits its 2D starter) and a PLACEHOLDER of its shape in every photo slot and
      question picture - never a blank; a sheet made before placeholders existed: --fill-slots. A placeholder never ships.
2  read course-visuals\kit\CATALOGUE.md - one line per kit part, the spec format, marks and steps. Never kit.js.
      A question's drawing keeps its own shape on the task page; a labelling question adds a band above and below it for
      its label boxes. A "ghost" label is still laid out (leaders go round it); a valve's OPEN / CLOSED: "state": false.
3  fill the build sheet (each slide's picture, layout, the photos) and EDIT the starter specs - never write one from nothing
      Several photographs on one slide: "tiles": ["assets/img/a.jpg", {"photo": ..., "caption": ...}] (each opens full
      screen); cuts of one document: add "tiles_as": "strips" - never a hand-written fragment. A slide has a
      "figure" or "tiles", never both: both are a problem.
4  python compile/scripts/build_module.py <course> --module 1            again after every change, until PASS
      ONE command runs everything: every figure on its real slide at once (auto-fixes what has one right answer), the
      compile and its drawing check, the words (instructor + trainee), navigation, the audits at 1280x800, 1024x768 and 1280x720,
      the course pages and the classroom's importer. It prints only what fails - file, slide or question, what to do -
      and one PASS line. Do not run those checks one by one: each separate run is a turn of the model.
      (L64) It starts with the PRE-CHECK (compile/scripts/precheck.py - a second, from the files alone): a picture
      the sheet names that is not there, an unknown template or variant, a photograph under 800 px (unless its
      _photo_meta.json record says why in "low_resolution_ok") - "FAIL M01 - nothing built: the pre-check found ..." and
      nothing is built until it is fixed. More words than the word guideline (`knowledge/theory-rules.json` `slide`) is a
      note, never a stop. Run it alone any time: python compile/scripts/precheck.py <course> --module 1. Under the first
      PASS: "TIME M01: <n> min from its starter build sheet to its first PASS" against the gold standard, 30-40 min a module.
      A module ALREADY BUILT is rebuilt as a fix, not here: scripts/fix.py rebuild <course> --modules 1 (fix/GUIDE.md 3b).
      A rebuild judges again only the slides and task pages changed in anything they load since their last clean check
      (the drawing check and the audits; the figures already did) - a failing one is judged every time, --full judges
      everything. Hidden browsers come from ONE pool for the whole computer (a quarter of the cores, 2-8,
      CF_BROWSER_SLOTS): two builds, or a build and the test suite, queue instead of overloading the PC. Each slot keeps
      ONE Chrome, each page in a new browser context (browser_slots.run_dom; CF_CHROME_REUSE=off starts a fresh Chrome
      per page).
      A slow build is measured, not guessed: set CF_TIMING=<file.jsonl> and every hidden-browser run writes its real
      seconds and its page clock there; `python course-factory/scripts/cf_timing.py <file.jsonl>` adds them up.
      A build that runs past 9 minutes answers "STILL BUILDING" (exit 3) and goes on by itself: run the SAME command
      with --wait for its answer - never a second build meanwhile. A module's FIRST build waits its turn behind another
      module's first build on the same computer (a queue - at most 45 min, CF_COLD_WAIT). --long-pole (the whole-course
      workflow gives it to the course's biggest module, scripts/build_order.py): its first build never waits.
      The answer says each problem ONCE with its fix and its file - a figure is one line per kind of problem
      ("FIGURE s03 - <spec> (scale 0.70 in a 480x238 px panel): small text x11", an example, the fix, the studio
      command); the audits per slide and kind with a count; the same compile line once with "(xN)". Every line is in the
      full log; --full-output prints them all.
5  on PASS - or MODULE CLEAN in a parallel build (--no-course-pages: only the course package left, judged after assembly)
      - it has walked the deck (every slide at every stop) and every task page like a trainee - each question of the
      self-checks and the module check as asked (1280 x 800 and 1024 x 768), answered wrong, answered right, and each
      page's last screen - into working_claude\_build\walk\MNN, and checked that every question grades right and wrong
      answers as such (a right answer not graded right, or a wrong one graded right, fails the build). Nobody has
      LOOKED yet: the WALK REVIEW (2i) is the one visual review of the module - slides and task pages, one reviewer who
      did not build it, two rounds at most - and the module is not done without it. There is no other sheet review: no
      screen is judged twice and none by nobody.
      In the whole-course workflow (orchestration/workflows/build_course.js) the BUILDER STOPS AT MODULE CLEAN; the walk
      judge reviews the walk beside the QA agent (who looks at no screen), and a BROKEN finding or a walk fail sends the
      module back for one fix round. Under MODULE CLEAN the build prints "WALK REVIEW - ..." : where the module's walk
      review stands. What could look better but is not wrong is never fixed in the loop: list it for the operator - a
      fix to a drawing that already passes can break it again (IGF M02 s02: PASS, then four failed builds).
6  THE POLISH ROUND - once, after PASS (or MODULE CLEAN) with every BROKEN finding fixed and the walk review passed with
      a round left, on the best model (opus), about ten minutes: work down the judges' POLISH lines (and MNN_POLISH.md
      when there is one) most visible first, one item at a time - scripts/fix.py polish begin <course> --module 1 --what
      "<the item>", the change, then fix.py polish check <course> --module 1: it builds again and, if the module no longer
      passes, puts the snapshot back by itself. Only layout, sizing, placement, cropping and label positions; never the
      approved words, an outcome or a fact. Here, and only for the items on the list, a drawing the build did not name may
      be changed. polish begin refuses after the time box; then fix.py polish end <course> --module 1, the kept items off
      the list - the rest stays for the office. A kept change makes its slides stale to the walk review: walk_review.py
      prepare --stale and a reviewer who did not polish it look at them (its second round).
   A FIGURE problem (from the build or the review): fix it in the studio, not in build after build -
      course-visuals\kit\scripts\studio.py <spec> --step all judges one figure at every step in seconds, on its real
      slide or task page. The build lists each finding's spec part ("[part TK1]") and those parts' numbers
      together: change them together, try in the studio until clean, then ONE build_module.py run. While only figures
      fail, build_module.py stops after them (a figures-only round, ~1 min) and runs the rest once they are clean.
```

- **A figure problem** is reported once per figure and part, with the step. `figure_fit.py` has already tried the fixes
  with one right answer: a drawing lost in empty space is cropped to what it shows; a drawing whose column got narrower
  (a layout changed) is re-fitted to it. Kept only when every audit is clean (figures\M01\_fit\ - the spec is never
  rewritten). When it gets close but not clean, the build writes the attempt over the spec itself when it adds no
  meaning BLOCK (the spec as it was: `_fit\sNN.sNN.before.kit.json`) - fix only what it lists; an attempt it could not
  apply is saved as `_fit\sNN.sNN.candidate.kit.json` with the reason. A studio probe whose page and every file it loads are
  unchanged is answered from `working_claude\_build\studio_probes` (the same report; `CF_PROBE_CACHE=off` measures every
  time).
- **A rebuild of a course that was fixed by hand** starts from the hand-fixed drawings: `--init-build --seed-from
  <predecessor course>` (or `"seed_from"` in `working_claude\course.build.json`) gives every slide and question whose words
  are unchanged the predecessor's drawing (the kit spec its DECK shows, else its source spec or .html / .svg drawing) or
  photo with its places, marked `"_seeded"`; only the rest get starters. The whole-course workflow passes its `seed_from`
  argument to every `--init-build`. A seeded slide keeps the predecessor's WHOLE entry (its layout keys - figure_first,
  split, boxes, inset ... - were fixed by hand with the drawing); a picture the predecessor keeps in its module folder
  (`assets/fig`, `assets/img`) comes with its record from `_figure_meta.json` / `_photo_meta.json` (never one without a
  record); a hand-made drawing brings the module files it is drawn by (the sheet's `styles` / `scripts` / `inline`).
  **Seeding is for quality, NOT speed:** drawings fixed against an older kit mostly fail today's checks (words under the
  12.5 px floor, hand-made scenes' contrast). Seed a course whose predecessor was built with the current factory, or
  accept the fixing time.
- **The whole-course workflow** builds the modules biggest first (`scripts/build_order.py`: screens, drawn figures, 3D
  scenes from the approved scripts, seeded ones counted less) in a rolling pool of `wave` at a time; its builder reads
  `compile/BUILDER_CARD.md`, not this guide. A module with a 3D-kit scene gets the 3D step after its build:
  `course-visuals/kit3d/scripts/scene3d_check.py <course> --module N` (spec check, smoke3d, perf3d, perf_gate's walk - a
  scene that lags in two walks fails the step - and a picture of every step in `working_claude\review\MNN_3d\`; longer
  than 9 minutes it says STILL CHECKING and is waited for with `--wait`), then a reviewer who did not build the scene judges the pictures. The 3D
  step, the figure step and QA judge the built module at the same time, and ONE fix round takes every BROKEN finding
  of the three (two builds, at most six studio runs a figure); then only what was BROKEN is judged again.
- **Figure fits**: the COLUMN re-fit tries one width at a time and stops at the first clean fit, and measures a figure
  at most 16 times (CF_FIT_MEASURES; every real fit on record was found within 11). An EMPTY drawing on a task page is
  cropped by itself, as a slide's is, and kept only when the page is then clean.
- **A task question a real photo of the module can carry** is answered on it: the compile names the photo and the
  build-sheet line in "To fix", or the sheet says why not, `"photo_declined": "<why>"`.
- **The figure shows what the slide says.** A kit readout (a part with a `"unit"`) must agree, at the end of a step,
  with the number its step's line states for that quantity: "fuel gas below 1 % of the LFL" with the LFL readout at 2 is
  a problem ("below" / "up to" / "above" / an alarm level are read as such). A photo whose own record says it is "not a
  X" may not sit on a screen whose words, alt or caption name X. On purpose: the build sheet says why -
  `"numbers_differ": "<why>"`, `"photo_ok": "<why>"`.
- **Effort.** The mechanical loop - build, read the failure, change a number in a spec or a key in the build sheet, build
  again - needs no deep thinking: it can run at medium effort. Keep high effort for the design decisions: which picture
  teaches the slide, what a figure shows, 3D or not, what the operator must be asked.
- **A parallel build** (one agent per module): add `--no-course-pages` - one process writes COURSE.html (§5).
- **A revision** (operator corrections): words through `content_script.py propose` -> `apply`; layout and figure changes
  in the build sheet and specs; then step 4 once.

Read this lane when a module's script is approved and its presentation is built. **The words are typed once — in the
script.** `compile/scripts/compile_module.py` writes `modules\module01\presentation\index.html` from it with the
factory's own frame, style files and deck engine. Nobody edits that file by hand. Why: `docs/PROPOSAL_SCRIPT_COMPILER.md`.

```
python compile/scripts/compile_module.py <course> --module 1 --init-build   once: a starter build sheet (landing rule,
                                                                            pass mark from the course's other sheets; a foot;
                                                                            an entry per tap / label question)
python compile/scripts/compile_module.py <course> --module 1                build (again after every change)
```

`build_module.py` (the Quickstart) checks that the words are the approved ones (`check_script_match.py`) as part of its one run.

**The module's design files.** Both `--init-build` and every compile first check the module's design files (style
files, engines, `kit.js` ...) against the factory's with `design_system.py`'s own check, and **say what they did**, on
the first line: *all N are the factory's own - nothing changed*; or *Design files were missing in ... - installed the
factory's N*; or *N were not the factory's current ones - updated from the factory: kit.js (older version) ...* (files
that only fell behind are put right, so a build never runs on an old `kit.js`). A file **edited inside the module** is
different: the build stops (exit 2, nothing built), names the file and gives the exact `design_system.py install <module>
--update` command (or, if the operator chose the different look, `design_choices.py add ... --rule shared-design`).
**`--module final`** builds into the folder after the last planned module (architecture.json's modules + 1: 15 planned
gives `module16`); with no architecture to count in, give `--module-dir`.
**A final with two variants** (FA, FB) is two graded pages: `assessment\final_a.html`, `assessment\final_b.html`
(PASSED / NOT PASSED, the pass mark, one answer-key section each; the deck's slides are Check slides, the landing card
and the start page say "Final assessment A / B"). A single variant stays `assessment\final.html`.
**Groups of trainees** (the script's `"groups"`, a question's `"group"`) are not variants: every set page - self-check,
module check, each final variant - is one page for the whole class that opens on *Which group are you in?* and then
shows the questions for everyone and the trainee's group's own (`data-group` on the question's section, `#grpScr`,
`#grpLbl`; gb_answer.js). A final stays blind (L27): the group screen tells nothing about the answers, and the pass line
on its start screen is each group's own count (`data-grp`). FA / FB keep their meaning - the second form for a re-sit -
so groups and variants combine: FA and FB may both carry grouped questions. The answer key marks each question's group
and each group's count.
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

The navigation check, the course-package check and the layout audits (`audit_deck.js`, `audit_collide.js`,
`audit_compose.js`, and the drawing check `audit_drawing.js`, §2e) are run by `build_module.py`; the compiler does not
prove a layout fits, the audits do.

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

**Every slide is one of the layout templates (L61; twenty of them).** Each one's slots, what fills them and its live
reference, one line a template: `course-module-ui/knowledge/blueprints.json`. The compiler chooses it from the rows
below and names it on the slide: `data-template="explain-figure.v1"` `data-variant="figure-right"`
(`course-module-ui/knowledge/layout-templates.json`). `gb_layouts.css` gives it the brandbook's colours, the official
logo top right, Raleway bundled. What the compiler chooses on its own:

| The slide | Its template |
|---|---|
| a photograph full screen / beside the words / in its own column | `photo-explain` `full` / `split` / `column` |
| a drawing on a stage | `figure-stage` |
| a picture beside up to 60 words | `explain-figure` `figure-right` (`figure-left` with `"figure_first"`) |
| a picture beside more than 60 words | `reading-with-figure` - or `long-explanation` when the picture is 3D |
| a picture beside more than 85 words | `reading-with-figure`, the words whole (never paged by the factory - the script splits the slide, `t_over_budget`, L61); `content-in-parts` (the lines in order, in parts of about 75 words, a tab each) only when the script keeps it in parts on purpose (`"in_parts"`) or the build sheet asks for it (`"parts"`) |
| no picture and more than 120 words (the word guideline's `steps_from`), or `"parts"` in its build sheet | `explain-figure` `text-only`, its lines in the same parts: shown in steps |
| wide photographs - every tile, or the one photograph of a photo column, at least `top_aspect` (1.25) times as wide as high, read from the file - and words that fit under them (`under_top_row`) | the `figure-top` variant of `explain-figure`, `reading-with-figure` or `content-in-parts`: the photographs in a row across the slide, each box its own shape, the words under them, their points two a row. A tall or square photograph stays beside the words; `"variant"` in the build sheet decides it either way |

**Word budgets (measured at 1024 x 768 with these templates and the larger logo - `layout-templates.json`
`budgets`):** beside a picture 85 words, with a photo under the words 70, beside a photo column 85, under a photograph
across the slide 70, on a full-screen photograph 50, beside a framed photograph 50, a part 75. The compiler chooses by
them; a slide over its template's budget is a must-fix at the script (`t_over_budget`), and a slide built over its
layout's budget (a template asked for by name) is a `Note:` in the build's answer before the audit measures it.
| lines numbered 1, 2, 3 ... | `procedure` (`with-figure`, or `text-only`) |
| lines whose cells are separated by ` \| ` | `reference-table` - one row a line, the separator kept in the line (hidden) |
| a short slide with no picture | `explain-figure` `text-only` |
| the opener / the recap / a task slide or room activity | `opening` / `recap` / `task-launch` (`tablet`, `check`, `room`) |
| a slide whose own words ask for it: `"claim"`, `"choices"`, the `"ask"` and `"reveal"` of a worked example, an explain-then-reveal or a predict-then-reveal slide, `"points"` (with an `"ask"` and `"reveal"`, the room's turn under the points), `"drill"` | `true-false`, `scenario`, `worked-example`, `long-explanation` `points`, `drill` |
| `"ask"` and the build sheet's `"spots"` / lines `"value \| meaning"`, no picture / `"figure_b"` and lines `"A \| B"`, `"what \| A \| B"` | `name-parts` / `key-numbers` / `before-after` |

**Word budgets** (measured at 1024 x 768 with these templates and the larger logo - `layout-templates.json` `budgets`):
beside a picture 85 words, with a photo under the words 70, beside a photo column 85, under a photograph across the
slide 70, on a full-screen photograph 50, beside a framed photograph 50, a part 75. The compiler chooses by them; a
slide built over its layout's budget (a template asked for by name) is a `Note:` in the build's answer before the audit
measures it.

Asked for by name in the build sheet: `"template"` (any of the first thirteen - the last seven come from the slide's
own words, `script/GUIDE.md` §1; `compare-two` needs `"blocks": [[1, 2], [3, 4]]`
and `"figure_b"`, `three-content-blocks` needs three `"blocks"`), `"variant"`, `"split": 0.5`-`0.6` (the text's share),
`"box"` (the picture's box, below), `"parts": [[1, 4], [5, 9]]`, `"panel": "light"` (a drawing made for a white page; the panel is Navy otherwise). An
unknown or unsuitable template or variant is a problem with the slide's id.

**Parts turn like pages.** The parts' number tabs are a strip at the foot of the slide body (56 px targets); Next, Back and
a tab turn the part like a page of a carousel - the words slide out and the next part's slide in (`gb_deck.js`, transform
and opacity only, at once under reduced motion). `"part_figures"` gives each part its own picture, in the order of the
parts: `[null, "assets/img/b.jpg", ["assets/img/c.jpg", "assets/img/d.jpg"], "s07b.kit.json"]` - a photograph or a
figure spec as `"figure"` takes it, a list of photographs as `"tiles"` takes them, `null` the slide's own picture. With
part pictures the picture turns with its words; with one picture it stays and only the words turn. A part's picture is
never a 3D model (one 3D scene a slide) - the slide's 3D scene is its `"figure"`.

**`"blocks"` ask for their template without naming it (2.127.0).** Beside a picture, `"blocks"` of three line ranges is
`three-content-blocks`, and `"blocks"` of two with `"figure_b"` is `compare-two` - `"template"` is not needed (before, the
blocks did nothing without it). A sheet that names a template, or a layout other than the starter's `two-col`, keeps its
own way. Every build prints the templates the deck is built in, most used first - `Templates in M02: 9
reading-with-figure, 4 photo-explain, ... (5 of 21 templates)` - and, when the script check finds the module mostly plain
with slides that fit a template, `MUST FIX (the slide for the information)`: the writer's finding, as `v_paged_slide` is
(`script/GUIDE.md`, "The check reads the plain slides for you").

**The layout plan (L62) - the deck's shapes, chosen like an engineer would.** Every slide blueprint is a file of
`course-module-ui/knowledge/blueprints/` that says its shape and what it is good for: the pictures it takes, the picture
shapes its box suits, the words it holds (measured budgets). Before it builds a slide the compiler scores, for each teaching
slide, every blueprint of its kind against the picture's real shape (a photograph's pixels, a 2D drawing's size, a 3D
scene's home view - `layout_plan.py`) and its words, then plans the whole deck: never the same shape twice in a row
(beside, top, bottom, stage, photo-full, words, two - a picture left or right is one shape), beside on at most about half
of the teaching slides, at least four shapes in ten where the slides fit them, near-equal fits settled by a choice seeded by
the course and the module (a rebuild is the same). A wide photograph or a wide drawing / 3D scene takes a band across the
slide with the words over or under it in two columns; a tall picture a tall box beside the words; a picture beside words
gets a box of its own shape, the words and the picture centred. A slide whose build sheet names a template, a variant or a
layout keeps it; so does a slide that fits one shape only - `Layout plan (M01): ...` and its `Note:` lines say each.
Words are never cut or moved. A slide the plan moved carries `data-varied`, so `build_module.py`'s pre-check measures it
and a shape it does not fit is not planned again (`MNN_layout_avoid.json`). The package check refuses a deck that breaks
the shape rules where its slides fit another blueprint (`data-shapes`). `CF_LAYOUT_PLAN=0` builds each slide in its own
template (the factory's own tests). More than a fifth of slides on the dark ground is a `Note:`, never a problem. A
slide whose OWN layout does not fit (the
larger logo can cost a long title its first line beside it) is yours: give it `"parts"` or a shorter picture column, as for
any slide that spills. A photograph under
1600 px on its long side is enlarged once (Lanczos, a light sharpening, at most four times; the original kept in
`working_claude/photo_originals/M01/`); under 800 px it is listed - a larger original is still the real fix.

**The picture's box.** A picture beside words gets one of four boxes (`layout-templates.json` `"boxes"`,
`compile/scripts/layout_fit.py`): `text-wide` 40 % of the width, `even` 45 % (the default), `picture-wide` 58 %,
`picture-large` 65 %. The compiler counts what the picture shows at once - a kit drawing's labelled parts, a 3D scene's
labels, an SVG's words, a photograph's spots - and gives it the box those names need (up to 6 any box, 7-10 even,
11-15 picture-wide, 16-22 picture-large, 23 or more the whole slide; a 3D model picture-wide at least), the words what
is left. Growing is worth it while it costs the words at most one part more than the
even box; past that, or when the picture needs the whole slide and the words are more than 45, the compile stops on
the slide: make it another kind of picture - in steps (a few names a step), a 3D model whose names show on tap, the
picture on a slide of its own (`"composition": "stage"`), or fewer names. Each such slide carries `data-box`. When the
audit finds a drawing's words too small or its labels colliding, or the fit gate sees a picture only in part, the next
build's layout solver gives it the next larger box (`settled: ... its picture needed more room`). `python
compile/scripts/layout_fit.py <figure> --words N` says what a figure gets before a build.

**Checked at every build:** a split slide is 55 / 45 by default (50-60 % text when the picture is simple, never
80 / 20); over the word guideline's 80 words (`knowledge/theory-rules.json` `slide`) with no picture, a picture goes
beside the words or the slide is shown in steps - a note, never a stop; approved words are never cut, summarised or set
smaller, and the factory never pages them beside a picture - when they need more room the writer splits the slide or
gives it `"parts"`.

| In the script, or in the delivery file | On the screen |
|---|---|
| `layout` `visual_full` + a photograph | `.slide.photo` — the photo is the screen, the words over it; past 45 words the photo beside the words (`two-col`, the split photo) - set by itself, no build-sheet choice |
| `layout` `split` | `two-col` — the words left, the picture right |
| `layout` `visual_wide` | `stage` when the words are short (45 or fewer), else `two-col wide-right` |
| `"composition"` in the build sheet | overrides: `opener`, `flow`, `two-col`, `wide-left`, `wide-right`, `stage` |
| a photograph + `two-col` | the photo fills the right of the screen, the words on a dark scrim (`photo split`, fixed width) |
| a photograph + `wide-left` / `wide-right` | a real column layout: the words as wide as the layout says, the photo cropped to fill its own column, its credit line on the slide. Use it when the words do not fit beside a `photo split` |
| a photograph inside a figure fragment | keeps the slide's visible credit line (the photo's, unless the build sheet's `"credit"` says otherwise, or the fragment's own caption already has it) |
| a task slide | `activity` with its code, `data-task-href` to `tasks\sc1_<title>.html` / `assessment\check.html` |

The words: one line is a statement; several lines are a statement and its support list; a line starting
`• ` is a list item. Every line carries `data-i="1"`, `"2"` … so a figure that steps can light up its
own line: `document.querySelector('#s04 [data-i="2"]')`. A figure script registers its slide hooks as
`window.GB_HOOKS = window.GB_HOOKS || {}; GB_HOOKS.s05 = {enter: fn, leave: fn};`.

## 2b · Real photographs, and no empty space (L52, L53)

- **As many real photographs as possible.** A photograph as the slide's picture fills the screen (`visual_full`)
  or the right of it (`split`) - never a small photo in a column. Beside a drawing, add a real photo under the
  words: `"inset": {"photo": "assets/img/x.jpg", "caption": "On board: ..."}` (its credit is added for you).
- **Emphasis**, chosen per slide: `"boxes": [2, 3]` (two options, side by side in meaning), `"conclusion": 5`
  (the line the room must leave with), `"legend": true` (a stage drawing's lines as a numbered row). The term
  before " - " or ": " is set in bold automatically.
- **No empty space.** A drawing, animation or 3D model gets the wider column (`fig-wide`) and the column's
  height; words are at reading size (`.copy`). Before showing a deck: `audit_compose.js` (every screen composed,
  none weak), `audit_deck.js` (no spill, no overfill, no tiny labels), `audit_collide.js` - at 1280 × 800 and
  1024 × 768. Two floors: a label inside a drawing below 12.5 px on screen is fixed in the drawing; body text is at least 16 px.
- **Every drawing whole and clean (L54).** Also `audit_drawing.js`: no part pokes out of the hull, tank, room or box
  it sits in (draw the room along a sloping stern, or clip it), nothing is cut off at the drawing's frame, every label
  keeps 4 px clear of other shapes, lines and labels; a crossing that is meant is marked in the drawing (§2e). Every
  compiled deck also loads `gb_fit.js`, which widens a
  frame a drawing still reaches past and names it in the console - fix the drawing, then compile again.
- **Figures from the figure kit first; a custom figure is allowed (L55).** When no kit part shows the idea well, see §2i for
  `"custom_figure"`. `"s14": {"figure": "s14.kit.json", "dark": true}` - the spec lives in
  `working_claude\figures\M02\` like any drawing source (its format: `course-visuals/kit/SPEC.md`). The compiler puts it
  into the page as data with the deck's own step buttons (`.mediabar`: previous, next, replay), and loads `kit.css` and
  `kit.js` (installed by `design_system.py` like `gb_deck.js`) and, when the course made parts of its own,
  `assets\kit_parts.js` after them. Each spec step lights its slide line (`"line": 2` -> `[data-i="2"]` `.cur`, earlier
  steps `.lit`); entering the slide starts the figure at step 0. Check the specs first:
  `course-visuals\kit\scripts\check_kit.py module <module> --figures <figures\M02>`.
- **Draw a kit figure in the studio, not in the compile.** `course-visuals\kit\scripts\studio.py
  working_claude\figures\M03\s07.kit.json` draws the spec on its real slide (the script's words, the build sheet's
  layout, the module's styles) at 1280 × 800 and 1024 × 768, runs every drawing audit at the end of every step, and saves
  a screenshot - in seconds. Change the spec until it is clean, then compile once. The kit does the drawing work by
  itself: every label gets a clear place (a leader line if it had to move), no word is drawn under 12.5 px, boxes are as
  wide as their words, the frame grows or zooms to hold and fill, and the colours follow the panel (dark deck, light task
  page). A spec never places a label; a `"text"` with `"to": [x, y]` is a callout joined to that place.
- **A kit figure is laid out beside its words, and drawn to its panel (L53).** A figure whose steps light the slide's
  lines takes `"composition": "two-col"` (the words at reading size in the left column, each lit line a tap target for
  its step; `"boxes"` when the lines are separate items) - not `stage` with a `legend`, which leaves the explanation in
  a row of small cards. Draw the spec to the panel's own shape (about 416 × 254 in the figure column - `scales()` in a
  deck reports the real scale), crop what the steps do not show, and run `audit_drawing.js` (its EMPTY check) at
  1280 × 800, 1024 × 768 and 1920 × 1080, at step 0 and at the last step. `stage` stays for a figure that is the whole
  screen and has no lines to light.

- **Every picture opens full screen, a photo with what it shows (L51, L56) - nothing to ask for.** Every compiled deck
  loads L51's one viewer, `gb_zoom.js`: a tap on any picture opens it full screen (pinch / + / − to look closer); a
  photograph's record - what it shows and its credit - stands under it, written by the compiler from the photo's
  `description` in `_photo_meta.json` (write it for the trainee when the photo comes in; a photo without one is reported
  at build). A full-screen photo slide opens on a tap of its bare picture and has the ⤢ button. A generated picture
  (`"generated": true` in its record) gets no credit line and no label on screen, and is never an L57 thumbnail.
- **A drawing carries the real photos of what it shows (L57) - when its build-sheet entry says `"photo_row": true` or its
  why is `real-thing-recognition`; never unasked.** The compiler then takes the real things the drawn slide names - the term
  before " - " in its lines (with the kit figure's step number) and the drawing's own labels -
  and puts the matching photos in a row under the drawing (`.photo-strip`, at most four), each opening in the panel.
  Matched by `"shows"` in `_photo_meta.json`: give every photo the plain names of what it really shows, e.g.
  `"shows": ["bunkering station", "LNG bunker hose"]`. A photo of another module is copied in with `copied_from`; one
  awaiting a rights review is never used. Every real thing still without a photo is printed and written to
  `working_claude\PHOTOS_TO_TAKE.md` (the module's section is rewritten each build; `## Notes` is yours).
  Matching is by name only: when a matched photo contradicts how the thing is drawn (deck tanks under a drawing of a tank
  in its hold), say so in the build sheet - `"no_photo": ["fuel tank"]` with a `"_no_photo"` reason - and the thing goes
  on the list instead. Look at every thumbnail the build placed before showing the deck.
  **Not a thing.** The words a chart draws - an axis, a line, a zone ("Air line") - are no real thing: a figure
  made only of the kit's chart parts (`scale`, `bands`, `curve_chart`, `flammability`, `range_bar`, bare `text`) is
  skipped. For any other name that is no thing, `"not_things": ["air line"]` (with a `"_not_things"` reason) takes it
  off the list altogether - `"no_photo"` keeps it listed.
- **A planned photo that does not exist.** The build names every photo slide with no picture file. Find the real one
  first (project, factory library, a free licence - `course-visuals`). If none exists and the slide only sets the
  scene, an AI picture may be made - `nano-banana:realistic-visuals`: describe it, show the prompt and the price, make
  it within the course's approved picture budget (one yes per course, L47), record it `"generated": true` in
  `_photo_meta.json`. A generated picture sets a scene only: equipment a trainee must recognise is a real photograph or
  a drawing, never a generated picture. A real photo still missing is listed in `PHOTOS_TO_TAKE.md` - a list, never a
  stop and never a question to the operator. The course's own small pictures are reused, enlarged by the build
  (Real-ESRGAN).
- **A 2D figure - drawn with the 2D kit.** A graph, an object in motion or a concept is a short JSON spec,
  `working_claude\figures\MNN\sNN.kit2d.json`, named as the slide's `"figure": "sNN.kit2d.json"`
  (`course-visuals\kit2d\SPEC.md` is the format and says how the starter is composed; `demos.html` and `pm.html` show
  every part, `courses.html` the detailed scenes). The compile ships `kit2d.js` and `kit2d.css`; the deck's Next walks
  its steps; `fit_gate.py` fails a step where its words overlap, are cut at the edge or lie on a line. Give the spec's
  `size` the shape of the slide's picture box: a wide figure in a tall box is shown small. `--init-build` composes the
  starter for a chart, comparison, animation or interactive-diagram slide whose lines are not mostly equipment and
  spaces - the best fit of the slide's words whose look the 2D figures of the 4 slides before it do not have - with a
  `"_brief"` (what it shows, why this kind, what else fits): build it as it is, or make the kind that
  tells the slide better. Two 2D figures that look alike less than 5 slides apart fail the compile, which names what
  else the slide's words make. A `"_todo"` names values only the course's sources can give (a chart's points, a task's weeks, a
  grid's rows); the compile reports it until they are in and the key is gone. Equipment layouts and the tested IGF
  patterns keep the figure kit's starter.
- **A `model_3d` slide (L46) - drawn with the 3D kit.** Do not write three.js. Write the scene as a short JSON spec,
  `working_claude\figures\MNN\sNN.kit3d.json` (parts, labels, steps: `course-visuals\kit3d\SPEC.md` is the format,
  `PARTS.md` lists every part; finished scenes in `course-visuals\kit3d\examples\`), and name it as the slide's
  `"figure": "sNN.kit3d.json"` - `--init-build` writes a starter for it. Optional on the entry:
  `"poster": "assets/img/<picture of the model>.png"`, shown until the first frame and when there is no WebGL.
  Check the spec: `python -I course-visuals/kit3d/scripts/check_kit3d.py spec <file>`; then smoke-test the compiled deck,
  then measure it (both below). **Full screen, clickable labels, the tap, building the scene on the slide before (so the
  first frame is under 1 s), `window.__noPrepare` and `window.__scene3d` all come from the kit, unasked** - a spec never
  lists them. The compile ships `three.min.js`, `kit3d.js` and `kit3d.css` with the module (loaded before
  `GBDeck.init`) and reports a spec that still has the starter's `"_todo"` key.
  **A part the kit lacks** is added to the kit, not hand-written: `KIT3D.define(...)` in the module's
  `assets/kit3d_parts.js` (PARTS.md says how; the compile loads it after `kit3d.js`), promoted into the kit later, like
  the 2D kit's `kit_parts.js` (L55). Only if even that cannot draw the slide, the scene is the module's own three.js
  file in the build sheet's scripts (like M03's `m03_station3d.js`), built to `knowledge/media-and-tasks.json` →
  `three_d.performance` (one shared renderer, built with its slide, first frame within 1 s and 30 fps with the CPU
  slowed 4x). Such a hand-written scene must itself:
  - **build on the slide BEFORE it** (built when its slide opens it takes seconds on a throttled CPU): the slide
    before's entry in `window.GB_HOOKS` builds it hidden - geometry, materials, first render - and the 3D slide's own
    hook only reveals the canvas and draws; honour `window.__noPrepare` and report `window.__scene3d` as
    `measure/GUIDE.md` §2b says - the measuring tool reads it;
  - **answer a tap** (`three_d.interaction`, the rule in `course-visuals` SKILL.md): a tap - not a drag - on a part
    highlights it (blue glow, the camera frames it, its name shows); a second tap on it, or a tap beside the parts, puts
    the view back; the tappable parts are the ones the labels name; raycast only on the tap (`pointerup`), never per
    frame; buttons and taps share one mode. Reference: IGF M03 `m03_station3d.js`. A scene that only turns is not
    finished;
  - **follow its box** for Full screen: the deck engine (`gb_deck.js`) gives every 3D slide's box - `[data-3d-box]`,
    else the `.fig` holding the `[data-stage]` - a 44 px Full screen button in its freest corner (canvas, labels,
    buttons and hint go full screen together, Next / Back / the swipe off while it is, Esc or the button leave it);
    resize the renderer and camera on `window` "resize" and on the box's `gb3d-resize`;
  - **make every label that names a part a control for it**: `data-3d-part="<part name>"`, and register the scene's
    selection once, `GB3D.wire(stage, { select: function (name) { /* the same as a tap on the part; null lets it go */ },
    current: function () { return selectedName; } })`, calling `GB3D.sync(stage)` after a tap on the part itself. The
    engine makes such a label a button (focus, Enter / Space, a 44 px tap area, a second tap lets go) and keeps the
    deck's keys off it;
  - **put its control hint** ("Drag to turn - tap a part to look closer") in an empty `<div data-hint></div>` in the
    figure, filled by its script; the compile marks every `[data-hint]` `data-script-ignore`, so `check_script_match`
    does not fail on words the script never approved;
  - **use the factory's classes** (`fill fig`, `[data-stage]`); a class of the module's own (`m02-3d-col`, `cards4`,
    `m04-3d`) needs a rule in the module's stylesheet or a query in its script - a class nothing styles or finds is a
    defect in `audit_ui.py` / `check_task_pages.py`. Layout goes in the stylesheet, never in a `style=""` attribute.
    A `[data-stage]` in a wide column takes the column's own height - no module override needed.

  **After every edit of a scene (spec or file), smoke-test it in seconds** before the next build:
  `python course-module-ux/measure/scripts/smoke3d.py <deck.html> [--slide s05]` - the 3D slide alone (and the slide
  before it) in a hidden browser with a 15 s limit: its first frame, or FAIL when it throws, never draws or hangs the
  page (a hanging scene costs a build its 600 s waits). It also presses the Full screen button (the box fills the window
  and keeps drawing, it covers no word) and taps a label (its part selected, then let go) - FAIL otherwise.
  **Measure it**: `node course-module-ux/measure/scripts/perf3d.mjs <deck.html> --slides=all` (Node + headless Chrome,
  CPU slowed 4x, warm and cold first frame, fps; exit 1 over budget; see `measure/GUIDE.md` §2b).
  **3D only where the figure's `why` is `spatial` (section 2i); the factory picks no scene unasked.**
  `--init-build` gives a `model_3d` slide a starter scene entry: its figure (`s05.kit3d.json` - nothing goes into `"scripts"`), a
  `"_figure"` note on how to build it, and writes the starter spec itself (a label, metres, a view, parts guessed from the
  slide's words and laid side by side, each with a label, and a `"_todo"` to place them as on board - never overwritten).
  It also writes the slide's 2D starter spec (`sNN.kit.json`, 2.50.6), named in the entry's `"_2d"` note but not in
  `"figure"`: to keep a 2D figure, point `"figure"` at it and write
  `"declined_3d"` - then edit the starter, never write a spec from nothing (M01 benchmark run 5, s05).
  **A photograph wanted is never turned 3D:** `"photo_wanted": "<who asked, why>"` - on a build sheet screen, a script
  screen, or the script's top-level `"photo_wanted": {"s07": "..."}` (outside the approved screens, like `"declined"`) - is
  the reason a planned 3D slide may carry its photo. `"declined_3d"` at the TOP of the build sheet is an optional note.
  A 3D slide whose
  figure is not a scene (a 2D kit figure, an `.svg`, a photo - anything but a `.kit3d.json` spec or an `.html` figure holding a `[data-stage]`,
  `data-3d`, `data-scene` or a `<canvas>`) is a must-fix in the build and a note on the script's review page:
  "asks for a 3D scene; it has a 2D figure". To keep the 2D figure, write the operator's reason in the slide's entry,
  `"declined_3d": "<their reason>"`; it is not flagged again. The deck's `data-visual` and the plan then say the 2D
  kind it was built with, and a cue line that still asks to rotate, zoom, cut open, drag or "tap each part"
  of a picture that cannot is a must-fix, with a drafted line in `working_claude\script\MNN.cue_fixes.json` and the
  `content_script.py propose` command that shows it to the operator; or keep it with `"cue_kept": "<their reason>"`.
- **Only what a page shows ships.** After each build a picture of `assets\img\` that no built page names goes,
  with its record, to `assets\img\_unused\` (skipped by the classroom); name it in the build sheet again and it comes
  back. `used_in` in `_photo_meta.json` is written by the build. A tap / spot / label / read-the-instrument question whose
  subject a real photo of the module shows is listed after the build with the build-sheet line - a note.
- **Every photograph once in the whole course (L58).** A photograph shows on one screen; a repeat, in this module or any
  other, carries `"reuse_why"` in its slide's entry. A copy under another name is the same photo (same `url_or_origin`, or
  the same bytes). A thumbnail takes a different photo or none; a photo you placed (picture, inset, photo in a drawing)
  that is already shown is reported - choose a different one, none, or give the `"reuse_why"` (the earlier module keeps it). After photos change, build every module again.

## 2c · More build-sheet choices

| Key | What it does |
|---|---|
| `"legend": [2, 6]` | on a stage slide only lines 2-6 form the numbered row; the lines before go above the drawing, the rest below. Words that already start with their own number get no second badge |
| `"box_alt": [4]` | which boxes are grey - the other of two options side by side. Without it every box is blue: amber is only ever the line a stepping figure is on |
| `"groups": [{"lines": [2, 7], "class": "box z1"}]` | lines 2-7 in one box, the first as its bold heading (a zone with its list) |
| `"hooks": {"3": {"class": "m02-steptext", "data-step": "2"}}` | a figure script's handle on a line - a class word and `data-*`, never a look |
| `"inset": {..., "under": "figure"}` | the real photo goes under the drawing when the words fill their column. It takes ~220 px of the drawing's panel: when that leaves the drawing under ~60 % (a 640 x 390 spec keeps 47 %), the build says so - put the inset under the words, use `"over"`, or draw the figure wider and less tall |
| `"inset": {..., "over": {"x": 140, "y": 8, "w": 176}}` | the photo lies on a blank part of a kit drawing, in the drawing's units - the drawing keeps the whole column and its full size (a photo under a drawing would squeeze it). It still opens full screen. The drawing check judges it at every step (`inset`): the photo, its caption and its credit may not lie on the drawing's words, on a control (the step buttons, the chrome) or past the drawing - a short `"credit"` and no caption, on a blank corner, is the way |
| `"aside": "m02_s08_minis.html"` | small drawings that belong with the words |
| `"figure_first": true` | the drawing on the left, the words on the right |
| `"class": "m02-s3d"` | a hook for the module's drawing styles on the slide - only with a rule for it in the module's stylesheet (or a query in its script): a class nothing styles is an `audit_ui.py` defect |

A room activity with a drawing of its own (trace a path) is laid out like a teaching slide and keeps the classroom's
Task marks. A task slide links to its set's page (`tasks\sc2_*.html`, `assessment\check.html`) - built by §2d.

**A practical exercise gets its slide (`scripts/exercises.py`).** A module whose exercise forms are in
`course\to_review\exercises\MNN\` (or `working_claude\exercises\MNN\`) - the novikontas-practical-exercises skill's
`..._Trainee_v01.docx` and `..._Instructor_v01.docx` - shows each exercise on at least one slide: an `"activity"` screen
with `"exercise": "8.1"`, its minutes the form's duration (practice, in the module's hours) - or, when the script's
minutes already fill its allocation (the deck is the programme's theory part, as in IGF Basic), 0 deck minutes and
`"practice_minutes"` the form's time, the programme's practical part. `--init-build` and every compile that finds one
without its slide write the proposal - from the TRAINEE form only: what the trainees do, what they need, the time - to
`working_claude\script\MNN.exercise_slides.json`, to propose and approve like any change (`content_script.py propose`);
until then it is a build problem. The instructor form is named in the slide's cue as the copy to run it from; none of
its words reach a screen.

## 2d · The task pages

Every task slide that opens questions gets its page from the same script: `tasks\sc1_<title>.html`,
`assessment\check.html`, `assessment\final.html` (`final_a.html`, `final_b.html` for a final with variants). A real
photograph beside a question carries its credit as a line on the picture and the round ⤢ button that opens it full
screen, as on a slide; a control with ready / pressed positions on an operate-the-panel card is drawn with the kit's
`push_button`. The page is only its questions as markup; how a trainee answers, grading by `data-key`, the result ring,
PASSED / NOT PASSED and the classroom messages (`gb-task-done`, `gb-timer`) are the factory's one shared engine,
`gb_answer.js` + `gb_answer.css` (course-task-ux/assets, installed by `design_system.py` like `gb_deck.js`; the screen
rules are `course-task-ux` SKILL.md's). `--only tasks` builds only these.

- **Built: all nineteen ways of answering** an approved script can hold - single_choice, multi_select,
  read_instrument, hotspot, spot_the_hazard, match, categorise, label_diagram, order, and cloze, choose_and_justify,
  scenario, set_value, find_the_fault, spot_the_error, build_the_plan, timeline, compare, panel_operate, fill_matrix (a
  table the trainee fills cell by cell). No trainee task page is made by hand; the one engine grades them all, tap and
  drag only (L38, L42).
- **On a picture** (hotspot, spot_the_hazard, label_diagram, read_instrument) the build sheet names the drawing, keyed
  by the question's id: `"q01": {"figure": "assets/fig/m01_ga.svg"}`. Each answer's place is found by itself - the
  drawing's element with `data-name` equal to the answer's words, and in it the shape of class `hit` (rect, circle,
  or a path of straight lines; a group's `translate()` is followed), grown to a 56 px tap target. What the drawing
  does not name gets a box: `"areas": {"Funnel": [left, top, width, height]}` in % of the drawing, or the id of its
  element: `"areas": {"Accommodation": "hs-acc"}` - never guessed. The drawing's own labels (`#labels`,
  `[data-task-hide]`) are hidden.
- **A real photograph, or a figure-kit drawing, instead of an .svg.** The same `"figure"` may be
  `"assets/img/pump_room.jpg"` (a photo in the module's `assets/img` with its record in `_photo_meta.json` - use as many
  real photographs as possible: tap the place, spot the hazard, read the instrument, label the drawing) or
  `"m04_chart.kit.json"` (the deck's own kit spec, drawn still at its last step - never copy a kit chart into an SVG).
  A photograph has no drawing to find places on, so each answer's place is its box in % of the photograph:
  `"areas": {"Relief valve": [62.5, 31, 12, 18]}`; a missing file, record, credit or box is reported, an image-model
  picture is refused. A tap on it stays the answer - it opens full screen by its corner button. A kit drawing's places are
  its part ids or the words a part is drawn with (`"areas": {"Fuel tank": "ft"}`) - and a place drawn inside a part:
  a side-view ga's funnel and house, `"areas": {"Funnel": "G.funnel"}` (never a % box); `"kit_step": 2` (or a word of a
  step's title) shows another step; **`"unlabel": "answers"`** (the choice to make) takes the words off only the parts
  the answers name (`areas` / `labels`) and their callouts - a `text` part pointing at them (`"to": [x, y]` inside the
  part), one with `"for": "<part id>"`, or one whose id is `T_<part id>` - so the rest of the drawing keeps its words and
  does not read blank. `"unlabel": "all"` also takes every free `text` part and the deck's context words, and `["P1"]`
  takes exactly those ids. With `"answers"` or a list the words are laid out with the rest and then hidden (the spec's
  `"ghost"`), so the words left stand where the deck has them (taking them out would re-lay the rest and can put a label
  beside the wrong space). The same `"figure"` also puts a picture beside a single / multi choice, above match,
  categorise, order, cloze, scenario ..., and `"figures": {"Plan A": "assets/img/a.jpg"}` over a `compare` column. With a
  picture beside four choices - or beside the cards of a sort, an order or a match - the compiler lays them side by side
  on a landscape tablet, so no choice and no drop zone is ever under the Check bar.
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
- **A team task** - a task slide with `"team": {"size", "roles", "scope"}` in the script - is marked on the
  slide (`data-mode="team"`, `data-team-size`, `data-roles`) and on its page (`task-mode`, `task-roles`, `task-scope`
  metas), per `classroom-system.json` `team_task`. The engine shows the team's name and the trainee's role at the
  top when the classroom sends `gb-team`, and runs as an individual task when none comes. Scope `team`: the first
  tablet of the team to finish hands in the one answer with `scope: 'team'`; the others show "Handed in by ... for
  Team A" when the classroom says so (`gb-team-done`). Scope `member`: everyone answers. Any team size; a role
  never locks anyone out of the task.
- **Label the drawing:** the compiler adds a band above and below the drawing for the empty label boxes, so no box
  covers what is drawn, with a leader line to each place. Every box is as wide as the longest label needs, in two lines,
  with room for the tick, and placed by itself (`label_layout.py`): each as close to its place as the others allow, in
  the same order, never off the edge, onto another or under the ⤢ button. Leave `"box"` out;
  `"labels": {"Fuel tank": {"at": "sp-tank"}}` only names the place. A `"box"` given there still wins, and one too narrow
  for its words is reported. **Boxes that do not fit two rows as wide as the drawing:** a drawing shown narrower than
  the screen - a 2:1 drawing under its bands is as tall as it may be and only ~560 of the row's 1240 px wide - gets rows
  that reach past it on both sides, as far as the drawing keeps its size (`task_pages.label_side`); five two-line labels
  then fit three below and two above. Only what not even the screen's width holds is reported.
- **The page:** the course's first self-check opens with "try your tablet first" (`"try_tablet": false` on the task
  slide's entry to leave it out); a check opens with its pass mark - the approved script's `"pass_mark"` (corrected like
  any other word: `content_script.py propose` with `{"script_field": "pass_mark", "new": 80}`), else
  `"pass_mark": 70` at the top of the build sheet; both, and different, is reported.
- **The instructor's answer key:** `assessment\check_answer_key.html` is compiled with the task pages from the
  same approved script - every question of every set in order, how it is answered, the right answer in the script's
  words (the letters the tablet shows, the order, the gap's words, the dial's accepted values), the feedback, and how
  the pages mark with the pass mark. Instructor-only by its name; `compile_course.py` lists it on START_HERE_EXTENDED.
  No key is typed by hand (a typed key falls behind the corrected script).
- **The instructor's plan:** `instructor\M01_PLAN.html` is compiled with the deck and the task pages
  (`--only plan` builds it alone) - allocated against built minutes on its face (a mismatch is shown and reported), the
  Main ILO and Sub-ILOs with where each is taught and checked, every screen with its minute and the script's notes, every
  task set with its pass mark and questions, the room activities with their link hints, the equipment and the sources.
  The Main ILO, the programme topic and the Sub-ILOs are in English (L19): a programme in another language by the
  rendering written at Stage 2 beside its words (`architecture.json` `"text_en"`, `"topic_en"`); a missing one shows the
  programme's words and is reported (exit 1). The ACP and the two tablet plans (`additional_materials.py`) the same.
  Never typed: correct the script and compile again. A plan changed by hand (or made before the compiler) is kept until
  `--force`.
- **Layouts the engine picks by itself:** a drawing to tap that is not wide (width / height < 1.8) takes the
  screen's height with the explanation beside it; a list of 6 or more to order, build, match or rebuild has its
  numbered places beside the cards; a task slide in the deck shows the gesture its set mostly asks for (choose, tap,
  drag, order, dial, find, gap) instead of one tablet icon.
- **Before showing it:** `check_script_match.py --part trainee` and `check_course_package.py`. The drawings are
  checked by the build itself (§2e), question by question - a drawing shared with the deck is checked again here,
  without its labels and at task size.

## 2e · Every drawing checked at every build (L54)

Nothing poking out, nothing cut off, no crowded label, no drawing lost in empty space - **anywhere**, and not left to
memory: after writing its pages `compile_module.py` opens each in a hidden Chrome or Edge at 1280 × 800 and runs
`audit_drawing.js` on it (`drawing_check.py`) - the deck slide by slide, a task page question by question. Every
finding is a problem to fix before the module is shown (exit 1), named by page, slide or question and part. A crossing
that is meant is marked in the drawing (`data-may-cross`, `data-no-contain`, `data-may-overlap`), so the reason is
written down. No Chrome or Edge: the build says it did not check. `--no-drawing-check` only while working on a drawing.
`drawing_check.py <page.html> ...` checks any page by hand - a hand-built one too.
- **A drawing that moves is judged on every frame.** A running engine's pistons, a cylinder's piston, a vent's
  puffs, a flow: the check holds every endless animation still at 9 moments of one clock and reports what goes wrong on
  any of them ("on 1 of 9 frames of its motion"), so an unchanged spec gets the same verdict at every build. The kit
  lays its labels out clear of what a moving part sweeps, the `engine` keeps RUNNING clear of its pistons' whole stroke,
  and a `vent`'s puffs rise only into free air. A finding on a moving part is the spec's to fix; for puffs the build
  says how ("fix (vent)": lower the outlet).
- The screen's own words (Check, Next, Your score ...) are English for now; another course language is reported.

## 2f · The visual review - required (build-order step 16)

The probes measure what someone thought to measure; only looking finds the rest (invisible curves, a file path in a
credit, a broken "choose all", tap areas off the things they name). So **looking is a required step**, not a courtesy:

- **The look is the walk review (2i) - one review, of everything a trainee sees.** The deck's slides at every stop and
  **every question** of every task page (self-checks, the module check, the final assessment's variants) - as asked at
  **1280 × 800** and **1024 × 768**, answered wrong and checked (every tap area and drop zone outlined by a review
  overlay), answered right and checked, and the page's last screen. Not a sample. One reviewer who did not build the
  module reads contact sheets (never a browser: 2.50.0 - the M01 benchmark's browser-driving review took 100 model
  calls and a third of the module's cost; the main session never views the pictures) against the walk's two rubrics,
  signs, and the module is not done, and not uploaded, without it. The older review of task-page sheets
  (`REVIEW_PROMPT.md`, `--reviewed`, `working_claude\review\MNN`) is gone: its points are in the walk's task rubric,
  so no screen is judged twice.
- **What the script checks, so nobody has to look for it:** each question is answered by its own keys **once right and
  once wrong**, and a right answer not graded right (or a wrong one graded right) fails the build ("choose all" keeps
  every tapped option and scores a fully right answer as right) - `build_module.py`'s "task pages" stage
  (`course-module-ux/measure/scripts/review_sheets.mjs <module> --walk-dir=...`, which also takes the walk's pictures;
  `--grade-only` in Phase A and in a check build with `--no-walk`).
- **After:** fix what the walk found, build again, and the reviewer sees only the slides and task pages that changed.
  `compile_module.py` prints this under **Next** after every clean build. A module is not handed over until it is done.
- **Two backstops that are cheap and automatic** (they do not replace the walk review): the drawing check (§2e) now also
  reports a part of a kit figure that cannot be seen on the figure's dark panel (`contrast`: a label under 4.5:1, a
  shape or line under 3:1; the kit's own parts are exempt; `data-low-contrast` marks a part meant to be quiet), and a
  credit, caption or full-screen record that shows a file-system path or a drive letter is a **build problem**.

## 2g · Phase A and Phase B - the picture decided as a KIND first, its CONTENT later

Choosing a picture is the one judgement in a build, so it is split off and everything else runs with no agent:

- **The script fixes each slot** (`script/GUIDE.md`): `"picture": {"kind": "photo|figure|3d|none", "aspect": "4:3",
  "shows": "..."}` - the kind decides the layout template before anything is built; the words a layout holds are a
  must-fix at render (a line over a part's 75 words), not a build note.
- **Phase A, no agent** (`phase_a.py`, or `--init-build` then `build_module.py`): a photo slot and a question's picture hold
  a placeholder (`placeholder.py`: a grey PNG of the slot's shape, 1600 px, marked in the file itself; a question's
  answers on a grid), a figure slot its starter spec, a 3D slot its kit3d starter. Every check that does not depend on the
  picture runs - figures, compile, words, navigation, every question graded right and wrong (`review_sheets.mjs
  --grade-only`, no sheets yet), the audits (which also measure each placeholder's px size, `data-slot`), the package.
  The answer is `PHASE A CLEAN M04` (exit 4) - never PASS while a placeholder or an unplaced 3D starter is left; and
  `check_course_package.py` refuses any placeholder, so none ever ships.
- **The needs file** `working_claude\visuals\M04_VISUAL_NEEDS.md` (and `.json`), written by every build: per slot its kind,
  shape, px size at 1280x800 / 1024x768 / 1280x720, the slide's words, what it must show and up to five candidates from
  the course photo catalogue; the figures still at their starter; the 3D scenes to place; the auto picks.
- **The course photo catalogue** (`scripts/photo_catalogue.py`): `index` once at intake (every old-course picture with
  its slide's words, every knowledge-base picture with its caption or page text, the sourcing pass's finds; the same
  bytes once), `assign` once the scripts are approved (each slot's five best by what it must show, its title, its words and
  the script's `from_old`; one pick per picture for the whole course - L58) and `visuals\PHOTOS_TO_FIND.md` for ONE
  visual-sourcer pass, which saves into `working_claude\photos_found\` with `"found_for": "M04 s05"`.
- **`--auto`** (`build_module.py --auto`, `visual_needs.py fill --auto`): a SLIDE's photo slot whose pick scored 0.6 or more
  and is 800 px or more takes it with no agent - copied in with its record, `"auto_picked"` in the sheet, listed in the
  needs file for the visual review. A question's picture never (its answers' places need the real things). A module whose
  slots all fill this way and whose figures pass from their starters is PASS with no agent - and still reviewed.
- **Phase B** reads only the needs file and `CATALOGUE.md`, runs `build_module.py --auto` first, fills the rest (a photo
  with its record; a question's boxes onto the real things; the 3D parts placed), then builds until PASS. In the workflow
  a module Phase A finished gets no builder at all (`build_course.js`).

## 2h · The upgraded slide bodies (L67)

Every compiled deck loads `gb_upgrade.css` and `gb_steps.js`; the compiler writes these bodies by itself, and Next walks
their stops. The approved words never change - only what is round them.

| Slide | What the compiler writes | Build sheet |
|---|---|---|
| the summary (`"recap": true`) | cards that open one by one on Next or a tap; the instructor asks the room first | - |
| a task slide | its words on the left with chips (minutes, the set's questions, alone / in teams); the exercise's `"photo"` on the right, else the tablet render | `"photo"` |
| numbered steps, no picture | step boxes, a badge each, a line under them that fills | - |
| `compare-two` | each card's first line its name, the lines under it boxes that Next lights | `"figure_b"`, `"blocks"` |
| `figure-stage` with two visuals | two columns, each its visual and its lines boxed under it | `"figure_b"`, `"blocks"` |
| a full photograph | a point lights on the photo with its line | `"spots": {"2": [x, y]}` |
| a split photograph | the photo zooms to the part the line names, a ring round it | `"zoom": {"2": [x, y, 2.2]}` (scale 1-4) |

| a full or split photograph, a carousel (2.109.0) | every photo stacked in the frame; Next walks the lines and the line's photo fades in (opacity only, L65); each opens full screen with its own record (L51, L56), credits in `_photo_meta.json`, never on the slide | `"photos": {"1": "assets/img/a.jpg", "2": "assets/img/b.jpg"}` |
| a predict- / explain-then-reveal slide (2.109.0) | the intro line is a lead, not step 1; the items are numbered, or lettered A, B, C when the task is to find the order | `"letters": true` / `false` (default: lettered when the question, title or lead says order / sequence / arrange / rank / sort), `"lead": false` (every line an item) |
| a worked example, or a slide with an `"ask"` and `"reveal"` (predict / explain-then-reveal, `points`), beside a kit figure (2.115.0) | each Next lights line k and plays the figure step whose `"line"` is k (and the steps before it); tapping a lit line replays its step. A step marked `"reveal": true`, or whose `"line"` is past the visible lines, plays on the answer's stop, so the answer shows ON the drawing. Each line is lit once; the question is one stop and the answer one stop, then Next leaves the slide. The answer opens under the question in the text column, never over a kit figure (a photograph keeps "the answer over the picture") | the figure spec's `"line"` / `"reveal"` |
| the module's ONE comparison table | 2-4 things side by side, a row a fact or a number (each row: its name, then one cell a thing), as the slide's picture on the white panel in the course's look, the words at reading size; its numbers are checked against the script and the sources like a figure's. Only one a module: a second is a problem, and so is a table with a `"figure"` or `"tiles"`. Any other table stays out of the picture (`check_kit.py` WORDS ONLY) | `"table": {"cols": ["LNG", "Methanol"], "rows": [["Flashpoint", "-188 °C", "12 °C"], ...]}` |
| a definition, a limit or a quoted regulation | shown whole at once: no step for Next to walk, its 2D-kit or figure-kit drawing as it stands at its last step. Steps stay where something changes, happens in order, or is revealed after a question to the class: a slide with `"ask"` / `"reveal"`, a task, a drill, the recap, or `"spots"` / `"zoom"` / `"photos"` keeps them (a problem names it). A slide without it steps as before | `"still": true` |
| a room activity with no `"opens"` (2.109.0) | no code on the slide (never the screen id); a text of three lines or more is a lead statement and bullets | - |

**Three checks keep a drawing honest (2.115.0).** Each is a must-fix that names the slide:
1. *Dead figure* - `its drawing never moves` (compile: no step of the figure changes any part from where it starts, e.g. a bar
   left at value 0 on every step) and, in the browser walk (`fit_gate.py`), `the drawing on sNN does not change on any Next`.
   A figure with no steps (a still picture) is exempt.
2. *The drawing agrees with the answer* - on a slide with a `"reveal"`, every labelled share (`composition_bar` segments) and
   every number with its unit the kit figure prints must be in THAT slide's own text, question, answer or notes, with the same
   value ("the drawing says 'Yard labour 20 %' but the answer says 'Yard labour 25 %'"). `20%` and `20 %` are the same. When the
   drawing legitimately differs, the build sheet says why: `"numbers_differ": "<why>"`, or cites the number in `"facts"`.
3. *Next walks the lines once* - `Next walks its lines twice` when a figure's steps name an earlier line after a later one.

`"spots"` and `"zoom"` are in the photograph's own pixels and keyed by line number; a wrong one is reported. A slide
without these fields is built as before.

`"photos"` is keyed by line number too: at Next number N the photo of the latest keyed line up to N shows; a line with no
photo of its own keeps the previous one, and the first photo (`"figure"`, or the first `"photos"` entry when there is no
`"figure"`) shows before any line. It needs a photograph slide (composition `photo`) and cannot be combined with `"spots"` or
`"zoom"`; a bad key or a file that is not a photograph is reported.

**Content in parts is the writer's finding, not a layout trick; the factory never pages by itself.** A slide with a
picture and more than 85 words - beside a 3D model on a split slide, more than 65 (its picture-wide box) - would need
parts with number tabs (1 2 ...); trainees find the switching confusing, and the compiler does not make them (no
automatic `content-in-parts` or `points` beside a picture, no pre-check fallback). It is stopped at the script (L61):
the script check (`content_script.py`, rule `t_over_budget`) makes it a must-fix - split the slide in two, or another
slide type - unless the script keeps it in parts on purpose (`"in_parts": "<why>"`, at most two in a module, never two
in a row). A slide that still reaches the build over its budget is listed by the review page
(`content_script.paged_findings`, rule `v_paged_slide`) and the compile as `MUST FIX (too many words for the picture)`;
`"parts"` or `"template": "content-in-parts.v1"` in the build sheet keeps the parts on purpose and silences it. The
build stops on words only when the fit gate measures them cut off or scrolling; a scenario or a worked example over its
template is stopped at the script too (`t_overfull`).

## 2i · Every figure has a reason, custom figures, and the walk review (2.116.0)

**Why (operator Aleksis Vējs, 2026-11-09, after the Project Management review: "draw the drawings 2d kit and 3d with a reason,
dont just put it in just because").** Every kit figure (`sNN.kit.json`, `sNN.kit2d.json`), 3D model (`sNN.kit3d.json`) and
custom figure carries `"why"` and `"why_text"` - in the spec, or in the figure's build-sheet entry:

| why | what the trainee sees | the steps must |
|---|---|---|
| `mechanism`, `sequence` | how a thing works / what comes in which order | be at least two, tied to lit lines (`"line"`) or a `"reveal"` |
| `quantity-change` | a number or level change | change a state value between stops |
| `comparison` | two states side by side | show two states (a step that changes the figure, or `"figure_b"`) |
| `spatial` | where things are, in space | - (a 3D model; refused when the slide's visual is a flat idea: chart, matrix, checklist ...) |
| `real-thing-recognition` | what the real thing looks like | - (also asks for the real photographs under the drawing) |
| `still` | one picture that needs no steps | - |

`"why_text"` is ONE sentence: what the trainee sees change, or sees. Refused: no why, no why_text, a why its steps do not
serve, `spatial` / 3D on a flat idea (`figure_why.py`; `v_why` in the content script, the compile before it builds, `check_kit.py`).
A slide may have **no picture** at all when its words read on their own - there is no picture quota anywhere.

**Custom figures - kit first, custom allowed.** When no kit part shows the idea well, draw a custom figure: a self-contained
`.html` or `.svg` file in `working_claude\figures\MNN\assets\figures\sNN.html`, named in the build sheet:
`"custom_figure": "assets/figures/s09.html", "why": "sequence", "why_text": "..."`. The contract (the same checks as a kit figure):
- **steps that Next drives**: `<script type="application/json" data-custom-steps>[{"line": 2}, {"line": 3, "reveal": true}]</script>`
  (steps keyed by line, a `"reveal"` step plays with the answer) and a hook `GB_HOOKS.s09 = {enter, leave, step(dir)}` where
  `step(dir)` returns true while it has a step to play - the deck's Next walks it; the figure changes on Next (the fit gate fails a
  drawing that does not - `dead`);
- **offline**: no `src` / `href` / `url()` / `import` / `fetch` to the network, no `<script src>` - the code is inside the file (a chart
  library only when it is already bundled in the plugin; otherwise hand SVG);
- **fits and does not overflow** (fit gate, audits), **smooth motion** (`audit_motion.js`, L65), **full-screen zoom** (it sits in the
  slide's `.fill.fig` box, so the viewer opens it like any picture).
A good custom figure is offered to the kit afterwards (`course-visuals/kit2d/SPEC.md`, "Custom figures").

**The walk review - "walk it like a trainee" (the module is not done without it).** `build_module.py` walks the deck at 1280x800
(`fit_gate.py --walk-dir`: every Start and every Next, a ~480 px picture of each stop, `working_claude\_build\walk\MNN\walk.json`)
**and every task page** (`review_sheets.mjs --walk-dir`: each question of `tasks\*.html` and `assessment\*.html` as asked at
1280x800 and at 1024x768, answered wrong with its tap areas outlined, answered right, and the page's last screen -
`walk\MNN\tasks\<page>\`, `walk\MNN\tasks.json`; a page with question groups is walked group by group).
When every other check passes it prints `NOT DONE: walk review missing/stale/failing/incomplete` until an AI reviewer has looked;
a module of a parallel build (`--no-course-pages`) prints the same under `MODULE CLEAN` (under `PASS`, when the course was assembled before), as `WALK REVIEW - ...`, and never fails on it. The factory cannot
call the reviewer. The final assessment is walked like a module (`--module final`: `walk\FINAL\`, `FINAL_walk_review.json` - the one
name the build, `walk_review.py` and the portal use). **In the whole-course workflow the walk judge runs it** (`build_course.js`: ONE
reviewer a module beside QA, for its deck and its task pages, reading the sheets in batches of up to 4; its fails in the one fix
round, one more look at the slides and task pages the round changed; one judge for the final after it is built); **in a build by
hand the lead session does:**
1. `python course-module-ux\measure\scripts\walk_review.py prepare <course> --module N --stale` - one contact sheet per slide,
   per task-page question (`<page>.<question>`) and per task page's last screen (`<page>.result`) that
   has no verdict for what it shows now (`walk\MNN\sheets\sNN.png`, `sheets\<page>.<question>.png`; the first time that is every one) and
   `walk\MNN\review_brief.md`: the sheets in batches of up to 4 slides with each slide's stop texts, its figure's why / why_text, its
   fails of the last review, and the rubric (1 something visibly changes on each Next; 2 the picture shows what the lit line says;
   3 nothing empty, hidden, cut, duplicated or contradictory; 4 a trainee knows what to do / what the slide teaches; 5 the drawing has
   a reason and serves it; 6 the answer / reveal is visible and does not cover the figure; 7 nothing of the factory's on screen - a
   file path, a placeholder, a cut credit; 8 the picture is the thing the words name and a seafarer would not call it wrong).
   **The task rubric**, judged per question: 1 the question and every choice readable and whole at 1280x800 and 1024x768; 2 the
   picture is the one the question is about and its tap areas / drop zones sit on the right parts; 3 the feedback explains and
   does not hand over a later question's answer; 4 nothing a trainee needs is under the Check bar; 5 usable with zero tablet
   experience - tap and drag, big controls (L42); 6 the last screen is the last: the trainee's own score and no way onward (L27,
   L45); 7 nothing of the factory's on screen. A task page is ONE fingerprint (the page and what it loads): a page that changes
   shows all of its questions again, and no other page's.
   (Pillow: `python -m pip install pillow`.)
2. **One Opus subagent at high effort per batch** (up to 4 contact sheets - several images in one look, never one screenshot at a time; the
   workflow's one judge a module reads the same batches itself): give it the batch's section of the brief and the sheet files; it
   returns JSON `{"reviewed_by": "...", "slides": {"s03": {"ok": true, "fails": []}, "s07": {"ok": false, "fails": ["stop 3: the
   chart is still an empty axis"]}}}` - `ok` a real `true` / `false`: the word `"false"` in quotes, or an `ok` with fails beside it,
   counts as a fail. **Never the agent or session that built the module or made the fix.**
3. Save each batch's JSON and `walk_review.py sign <course> --module N --review <reviewer.json> --built-by "<who built it>"`
   (`--built-by` once more for each agent that fixed it; the results merge by slide). It records who reviewed and everyone who built
   or fixed, and refuses a review signed by any of them, by nobody, or of a slide that is not what its contact sheet showed - a
   module built again while the reviewer looked: `prepare --stale` again and review the new sheets. The names are labels the caller
   gives: the script cannot tell which agent typed them, so the lead session passes the true ones.
4. **Fix every fail in one go, build again, and review once more:** `prepare --stale` then shows only the slides with no verdict for
   what they show now - the ones the fix changed. The walk keeps each slide's fingerprint, the one the audits' cache uses: its
   markup (build timestamps and comments ignored), the module's stylesheet and scripts, the shell, the files it names - a changed
   `gb_*.js`, kit part or photo makes its slides stale, a slide nothing touched keeps its verdict, and a slide that failed and was
   not changed keeps its fail and is not shown again. **Two rounds at most** - a third `sign` is refused, and a round is counted for
   the module, so renaming a slide does not start it over. What still fails after the second is the operator's:
   `walk_review.py verify <course> --module N` lists each one with its slide and stop, and the operator either accepts it -
   `walk_review.py accept <course> --module N --by "<operator>" --why "<why it may ship>" [--slides s04]`, recorded in the signed
   file and shown by `verify`, in the draft's notes and at upload from then on - or has it fixed and opens one more pair of rounds
   (`walk_review.py reopen <course> --module N --by "<operator>"`). After the second round a changed slide needs `reopen` first:
   `accept` is refused for a slide that is not the one reviewed. **`accept` and `reopen` are the operator's own**, typed by the
   operator - no agent runs them, and the file records how each was run (typed in a terminal, or not). An accepted slide that
   changes again is stale again. `--no-walk` leaves the walk pictures alone: the factory's own tests, and a check build that runs
   beside a reviewer.
`fix.py upload` and `course_portal.py upload` refuse while a built module's walk review - or the final's - is missing, stale,
incomplete or failing with nothing accepted; a slide or a task page that was never walked does not pass (`incomplete` - a
module whose deck is reviewed and whose task pages are not is NOT DONE), and what the operator accepted is listed at upload.
`fix.py check --kind walk --slides s03,self_check_1` walks and checks the slides and task pages a fix touched.

## 3 · When the look is not enough

If a slide needs something the shared style files cannot do, the answer is **never** a module style
file for text or layout — that is how modules stopped looking alike. Add it once to the shared files
(`course-module-ui`), so every module gets it on its next build. A module's own style file holds its
drawings' colours only.

## 4 · Safety

- Built only from an **approved** script; `--draft` gives a preview, marked as such, never handed over.
- A deck changed by hand — or built by hand before the compiler — is **not overwritten**; the change
  goes into the script or the build sheet, then `--force`.
- **A drawing fixed by hand in the deck is never undone by a rebuild.** When a slide's inline kit spec
  (`<script type="application/json" id="kit-sNN">`) differs from what this compile would write for it (the source spec
  after `figure_fit`) AND its section carries `data-sme` or an `<!-- SME: -->` comment, the compile stops (exit 2), names
  the slides and writes nothing. **`--force` does not skip it** - it only skips the "changed by hand" check, never a
  person's mark. Put the deck's drawings back into the source specs with
  `compile_module.py <course> --module N --import-sme-figures` (it writes only `working_claude\figures\MNN\sNN.kit.json`, a
  decision made on purpose), then compile with `--force`: that slide's spec is byte-identical to the hand-fixed one. To drop a
  fix instead, take the `data-sme` mark off that slide in the deck yourself. A slide without a mark behaves as before.
- A missing picture is listed, never invented.
- An inset photograph under more than about 75 words (90 on a photo split) is reported at build with the px it will
  spill - before the drawing check finds it. Cut the words, put the photograph on a task question, or lay it "over" a
  blank part of a kit drawing.
- The same script and build sheet always give the same file.

## 5 · The course's own pages

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

## 5b · The additional materials - the paper beside the tablets

Every course build (`compile_course.py`, or `compile/scripts/additional_materials.py <course>` on its own) writes the
paper an auditor, the office and the instructor need, from what is already approved - nothing in it is new content:

```
course\
  additional-materials\                     beside modules\ - never on a tablet (the publisher sorts it internal)
    INDEX.html                              every file below, linked - the office's way in
    acp\ACP_<course>.docx                   the Advanced Course Plan for the auditor
    acp\ACP_<course>.html                   the same plan to read
    practical-tasks\pdf\MNN_<code>_<title>.pdf     one per task: every self-check, team task, module check and room,
    practical-tasks\docx\MNN_<code>_<title>.docx   simulator or equipment exercise - what the trainee does, the right
                                                    answers and feedback, the instructor's notes, the marking
    simulator-and-equipment\Day_N\          what the instructor prints at the start of day N:
      MNN_<code>_<title>_TRAINEE.pdf / .docx       the trainee card - no answer, no instructor note
      MNN_<code>_<title>_INSTRUCTOR.pdf            the instructor sheet - the full description
    practical-kit\Day_N\                    the guideline's paper (L68), only from an approved instructor_led.json:
      MNN_<code>_<title>_PREBRIEF.pdf / .docx      the pre-brief card, read aloud before the run
      MNN_<code>_<title>_DEBRIEF.pdf / .docx       the debrief card, the observation card under it
      MNN_<code>_<title>_ASSESSMENT.pdf / .docx    the assessment form of a recorded run, one per candidate
    practical-kit\EMPLOYER_SHEET_<course>.pdf / .docx   one page for the company (`instructor-led/GUIDE.md`)
  modules\_course_shell\advanced_course_plan.html      the ACP on the instructor's tablet
  modules\moduleNN\instructor\advanced_module_plan.html   the module explained step by step, for the tablet
```

- **The ACP** follows the school's ACP: the course's facts (programme, standard, model course, hours and days, group,
  rooms, equipment, final assessment), the Main ILOs, then **day by day** - the day's training objectives (its modules'
  Main ILOs, word for word - in English, L19), and per module its number, topic, training method (presentation, self-checks, team tasks,
  the exercises with where they run, the module check), its Sub-ILOs and its used material (each source by its title),
  the questions to check the day (its module checks' first two), literature, films and the line for the person
  responsible (`course.build.json` `"responsible"`).
- **The days**: `course.build.json` `"days": [[1, 2, 3, {"module": 4, "minutes": 200}], [4, 5, 6]]` - delivery, like
  `"module_order"`; a module without minutes takes what is left of it. Without it, the modules in the course's order
  fill each day up to `programme.json` `max_hours_per_day`, a module split where the day ends. Set it from the
  programme's timetable when that splits a module differently.
- **A task's kind on paper**: simulator / equipment / room, from its own words and its practical's equipment
  (`architecture.json` `"practicals"`); `course.build.json` `"paper_tasks": {"M09.A02": "equipment"}` when the words
  mislead. Only simulator and equipment exercises go into `simulator-and-equipment\`.
- **The two tablet pages stand alone** - their style inline, no stylesheet, script or link out - so the instructor
  panel can open them over itself and close them again. Both are instructor-only by their folder.
- **PDF** is printed by the hidden Chrome or Edge (`browser_slots`) from a copy kept in
  `working_claude\additional_materials\`, and only when its page changed (`working_claude\additional_materials.json`):
  the first build of a 21-module course about 2 minutes, a rebuild seconds. `--no-pdf` skips it (said as a problem).
  A file it made before and no longer makes is moved to `working_claude\additional_materials\old\`, never deleted.
- A module whose script is not approved gets nothing, and is said. `additional_materials.py <course> --check` says
  what is missing or out of date. The headings and labels are English only so far; a course in another language is
  told so on every build (the course's own words are as approved).

**Languages (L19).** The words the factory itself puts on a task page (`task_pages.py` WORDS, the engine's in
`gb_answer.js`), on the deck (the deck engine's in `gb_deck.js` LANG, the landing card's in `compile_module.py`
LANDING) and on the start pages (`compile_course.py` WORDS) exist in English, Latvian and Russian, chosen by the
script's / architecture's `course_language` - the whole page in one language, `<html lang>` set to its code
("Latvian" is lv, never "la"). The lv and ru words are **PROVISIONAL** until a native speaker has checked them:
`compile/TRANSLATIONS_REVIEW.md` lists every one. Any other language is reported (exit 1) and the factory's words
on that page are English - never silently. A task page's file name is its title in plain letters (Vārsti → varsti,
клапаны → klapany). Every Novikontas course is in English unless one is explicitly made in another language.
