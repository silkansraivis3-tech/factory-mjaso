# Script compiler: the course is written once, as the script, and the factory builds the pages (2.25.0 – 2.49.2)

Branch `aleksis/script-compiler` → `main`. 57 commits, 127 files. Main has not moved since the branch started,
so it merges with no conflicts.

## In one paragraph

Before this branch the factory wrote every module twice: first the approved words (the script, `M01.json`),
then the same words again by hand as HTML for the deck, the task pages and the start pages. Every wording fix
had to be made in both places, and most of a module's build session went into hand-editing the HTML. Now the
script is the only place the words are written. A compiler reads it and builds every page a module needs.
Nobody edits those pages by hand. To change something, you change the script (or the build sheet for layout)
and compile again.

## What it builds

| From | The compiler builds | Script |
|---|---|---|
| `working_claude\script\M01.json` (the approved words) + `M01.build.json` (pictures, layout choices) | the instructor deck `modules\module01\presentation\index.html` | `compile/scripts/compile_module.py` |
| the same script | every trainee task page `tasks\*.html`, the module check `assessment\check.html`, and the instructor's answer key | `compile/scripts/task_pages.py` |
| the same script | the module plan for the instructor, `instructor\M01_PLAN.html`: minutes, screens, tasks, equipment, sources | `compile/scripts/module_plan.py` |
| all modules | the course's own pages: `COURSE.html`, `_course_shell\course_map.js`, each module's `START_HERE.html` and `START_HERE_EXTENDED.html` | `compile/scripts/compile_course.py` |

How to use it: `plugin/skills/course-factory/compile/GUIDE.md`. Why: `docs/PROPOSAL_SCRIPT_COMPILER.md`.

## What was added, in plain words

**The compiler (course-factory/compile)**
- The deck is built from the script, using the shell, colours and layouts the factory already had. Nothing new
  in the look.
- All 19 ways of answering a task are built: choose one, choose several, read an instrument, put in order,
  label a drawing, match, sort into groups, fill the gaps, tap the place, spot the hazard, choose and justify,
  set a value, operate a panel, scenario, find the fault, spot the error, build the plan, timeline and compare.
  Tap and drag only, no typing. One shared task engine (`course-task-ux/assets/gb_answer.js`)
  runs them all, so no task page has its own hand-written grading code.
- Team tasks: a team answers once or each member answers on their own tablet (2.39.0). The classroom app still
  has to confirm the messages this uses.
- The answer key for the instructor is built from the same script (2.45.0).
- Every module ends with the same recap slide, in the same design.
- Latvian and Russian for the parts the factory writes itself (buttons, start pages, task screens), marked
  PROVISIONAL until a native speaker checks them: `compile/TRANSLATIONS_REVIEW.md`.

**Figures: the figure kit (course-visuals/kit)**
- A library of ready-made drawing parts for technical figures: tanks, pipes, valves, detectors, fans, fire,
  gas clouds and more. 34 parts, all shown in `kit/GALLERY.html`.
- The kit lays out labels by itself so they don't overlap, keeps text at 12.5 px or bigger, and draws the same
  figure correctly on a light or a dark slide.
- Figures can step: each press of Next shows the next state, and each step is checked.
- A part a course needs and the kit doesn't have yet is made in the module first, then moved into the kit once
  the module is finished (`kit/PARTS.md`).
- The figure studio (`kit/scripts/studio.py`) shows one figure on its real slide, at every step, in seconds.

**Pictures**
- Real photographs first, everywhere, also on the trainee task pages (2.43.0).
- Every picture opens full screen with a tap. A photo shows what it is and its credit.
- A generated picture is never called a photograph.
- Each build lists the real photos still missing (`working_claude\PHOTOS_TO_TAKE.md`), so they can be taken
  at Novikontas.
- nano-banana 1.3.0: pictures can also come from the Gemini app in the browser, after the person decides.

**3D and AI pictures without being asked (2.49.0)**
- IGF M04, M05 and M06 came out with no 3D, and M03 – M06 with no AI picture: the factory only printed a vague note
  for the whole module, and it was ignored.
- Now the script writer plans them before the review page: a 3D model where a slide's lesson is a shape, an inside or a
  layout in space (about one good scene in a module whose subject is spatial), and an AI picture where a slide sets a
  scene that no real photo shows.
- What was left out appears on the review page as a proposal for a named slide, with the words that triggered it. The
  operator keeps it or strikes it; a struck one is remembered (`"declined"` in the script) and never proposed again.
  It is a proposal, never a block - your 2.18.1 rule.
- All the old limits stay: 3D on at most half the teaching slides and never instead of a real photo (L46); never an
  AI picture of equipment a trainee must recognise (L33); every AI picture still described, priced and said yes to
  before it is made (L47).
- On the pilot: nothing for M01 – M03 (each has its 3D scene); M04 s10, s06; M05 s06, s05; M06 s14, s06.

**Checks that run by themselves**
- After each build the compiler opens every page in a hidden Chrome or Edge at 1280 × 800 and checks every
  drawing: no text over lines, no label off its box, contrast, text size. If it finds a problem it says what to
  fix and exits with an error.
- The deck engine finishes animations before anything is measured, so the checks don't report false problems.

**Before any module is built**
- The ILO map and the knowledge base come first (L59). `ilo_map.py`, `course_gate.py`.
- `kb_tool.py` refuses a wrong `--course` folder instead of creating one (2.48.1).

**New laws:** L52 – L59. They are in `plugin/skills/course-factory/SKILL.md` and `docs/FACTORY_LAWS.md`.

## How it was tested (2026-10-16)

1. **All 35 test files in the repo pass**, including the new ones: `test_compile_module.py`,
   `test_compile_course.py`, `test_task_engine.py` (the task engine in a real browser), `test_module_plan.py`,
   `test_label_layout.py`, `test_kit.py`, `test_gallery.py`, `test_solver.py`, `test_studio.py`,
   `test_audit_deck.py`, `test_audit_drawing.py`.
2. **A real course compiled from start to end.** All five built modules of the IGF Basic pilot were compiled on
   a copy of the course, so the real folder was not touched. Result:

   | Check | Result |
   |---|---|
   | compile M01 – M05 | all 5 built, drawing check clean in every module |
   | `check_script_match.py`: the words on screen are the approved words | pass, instructor and trainee, all 5 modules |
   | `check_navigation.py`: every page can be moved through and left by tapping | pass, 39 pages |
   | `check_course_package.py` with the classroom's own importer | pass: 5 modules, 188 files for the tablets |
   | `audit_deck.js`, `audit_collide.js`, `audit_compose.js` in the browser | 77 of 78 slides clean, every slide composed, no overlaps |
   | `check_task_pages.py`, `audit_ui.py` | only small markers left, nothing visible (see below) |

   Two things in the pilot course itself (course content, not the factory) were needed first, and its real folder
   still needs them: run `design_system.py install --update` on each module, because its kit files were older,
   and `"rows": 2` in M02 s15's figure (already noted in the MANIFEST). One slide, M02 s08, has 20 px of text
   below the screen. The hand-built pilot deck had the same problem; the fix is fewer words on that slide.

3. **A new module built from nothing: IGF Module 6** (the real test - 2026-10-16, record in the course's
   `working_claude\M06_BUILD_METRICS.md`). Fact sheet, script (approved by Aleksis), 13 kit figures, 5 real photos,
   then compiled: 21 slides, 3 self-checks, the module check, answer key, module plan, start pages.
   - **84 minutes** start to finish, about 30 of them hands-on; the rest was helpers working in parallel.
   - **0 hand edits** to any HTML page. First use of "spot the hazard" in the course: built and graded correctly.
   - **9 compile runs** (Modules 1 - 4 had taken 3, ~10, ~12 and 17); 5 of the 9 would not have been needed with
     the fixes below.
   - Every check passes - words, navigation, the classroom importer, drawings, all three browser audits (21 of 21
     slides composed) - except the two open questions below.
   - 33 problems written down with file and line; none needed a hand-edit to work round. The two that cost compile
     runs are compiler bugs to fix: it crashes when run with `python -I`, and after that crash it refuses its own
     output as "changed by hand". The rest are layout limits (a photo slide cannot give the words more room),
     figure-kit polish, and missing kit parts (spark, lamp, a tank rupture).
   - **31 of the 33 are now fixed (2.49.1).** The compiler runs with `python -I` and survives a crash without
     `--force`; photo slides can give the words more room and keep their credit; task photos get alt text; new kit
     parts `lamp`, `spark`, `composition_bar` and a tank rupture / drifting gas cloud; kit labels on scales are laid out
     and checked; a new `run_audits.py` runs the browser audits without the browser pane. After the fixes, all 36
     test files pass and Modules 1 - 6 compile clean with `python -I` (M02 s15 needs its known course fix).
     Two left on purpose: a Retry button per question (against the task rulebook's "one opening, one result" -
     your call), and a photo on a `two-col` slide keeps the words-over-the-photo layout that M01 - M06 use.

4. **The rest of the course, built in one unattended run (2026-10-16), and what it found (2.49.2).** Modules 7 - 15
   and the final assessment were built in about 2.5 hours with no one at the computer, plus 3D scenes for M04 - M07.
   They are **drafts**: Claude Code's safety check rightly refused to let Claude approve its own scripts, so Aleksis
   approves each one. Every page builds and every check passes. The run logged 21 more factory problems; all are fixed
   in 2.49.2 - the main ones: every compile now updates a module's out-of-date design files (M01 - M06 had an old
   drawing kit that caused false findings), the final exam's two variants are both graded exams, drafts are kept out of
   the tablet package, task photos show their credit, and the 3D proposal no longer suggests procedure slides. Also new:
   **every 3D scene answers a tap** - tap a part, it glows and its name shows, as in Modules 1 - 3 (the new scenes
   only turned). After the fixes: 38 test files pass; all 16 modules compile on a copy, every drawing clean.

5. **Fixed while testing (2.48.2)**
   - `check_task_pages.py` reported every figure-kit state as "unstyled", because the kit writes those styles
     from its script. It now reads them. 213 false findings → 4 harmless markers.
   - `audit_ui.py` reported `var(--kit-up,1)` and the like as "voided", but a `var()` with a fallback still
     works. It now counts only a `var()` with no fallback. 38 findings → 8 (the compiler's `.hit` marker on
     tappable shapes, and a few classes in the pilot's own figures).
   - The current line of a stepped figure no longer has the amber bar on its left (`gb_compose.css`).

6. **Safety fixes from an outside review (2.48.3, nano-banana 1.3.1)**
   - Tablet publisher: a secret was ignored if the text `SUPABASE_ANON_KEY` was within 200 characters of it,
     so a service-role key right after it passed. Now only the key itself can be allowed: a key passes only
     when it decodes to the `anon` role. `--merge` no longer merges into `master`; the PR is merged in GitHub
     by a reviewer. **Branch protection on `master` in novikontas-training-app is still the real guard -
     please turn it on if it is off.**
   - nano-banana: a hard spending limit in code (5 EUR a day, 50 EUR a month on one computer, can be raised),
     a paid video is never lost when a status check fails, and when the client supports it each picture is
     also confirmed in the client's own dialog.

## Open: Raivis, your decision is needed (not blocking the merge)

1. **The hand-off screen.** Your ruling of 2026-09-03 (`floor.json`) is: module check second to last, hand-off
   screen last. The script does not allow any screen after the check, so compiled decks end on the check, and
   `check_static.py` reports 2 findings on every module. Should the compiler add the hand-off screen by itself
   (it is not content, so it doesn't need to be in the script)?
2. **Theory vs practice balance on compiled decks.** `check_balance.py` needs `data-active` (active minutes) on
   each block. The compiler doesn't write it yet. The script already marks active slides (L49), but if we copy
   that across, each active slide becomes a "100 % active theory block", which `check_balance` flags as a rename.
   Which rule should win?
3. **Not done yet, on purpose:** the editor (so an instructor can change the script without an AI session) comes
   later, in its own proposal. The Latvian and Russian wording still needs a native speaker's check. Real-tablet
   testing is yours (L39).

## After merging

Colleagues get it on their next plugin update (course-factory 2.49.2, nano-banana 1.3.1). Today the installed
copy on our computers is 2.24.0, from before the compiler. An existing hand-built
module keeps working. To move it to the compiler: `design_system.py install --update` on the module, then
`compile_module.py <course> --module N`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
