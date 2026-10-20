# Hand-off — script → HTML compiler (and later an editor) for the Course Factory

*Written 2026-10-15 by Claude for Aleksis Vējš. Untracked working note, not yet committed.
Repo: `silkansraivis3-tech/factory-mjaso` (this clone). Plugin `course-factory` 2.24.0.*

## 1 · The idea in one paragraph

Today the AI writes every module twice: first the content script `working_claude/script/M<nn>.json`,
then the same words again by hand as HTML (deck, task pages, start pages). Build a **compiler** that
turns the approved script into the delivered HTML, so the AI only writes JSON. Later, put an
**editor UI** on top of the same JSON, so an instructor can fix wording, reorder screens or swap a
task type without an AI session.

## 2 · Evidence that the problem is real

From the plugin (2.24.0, paths under `plugin/skills/`):

- `course-module-ui/templates/gb_shell.html:4` — "Paste this. Fill the CAPITALISED placeholders. Add your own screens."
- `course-factory/scripts/content_script.py` — `render_html` (:936) and `render_docx` (:1129) build only
  the *review* page and DOCX. Nothing builds the deck. `gb_key()` (:450) exists but is only used to
  check keys, not to emit them.
- `course-factory/scripts/check_script_match.py` exists to prove the hand-written HTML did not change
  the approved words — a check a compiler makes unnecessary.
- `docs/PHASE5_GAP_REPORT.md:145-160` — each module agent loads ~80k tokens of rules before its first
  slide; 8 modules ≈ 640k tokens of rules before any content.

From the live pilot (`C:\Users\aleksisv\Desktop\Kursi\Drošības pamatkurss\course\`, IGF basic, Module 1):

- About 1,700 messages in the build session for **one** 40-min module (16 modules planned).
- `working_claude/script/M01.json` has 20 screens; `modules/module01/presentation/index.html` was
  written and patched with the Edit tool. 31 `.slide` sections, only 11 carry `data-script`;
  11 of 20 script titles appear verbatim in the HTML.
- `working_claude/FEEDBACK_LOG.md` rows 4–17: every wording fix was applied to the JSON, then again to
  the HTML. Row 18: a layout bug ("the text is cut off") fixed by hand in this module only.

## 3 · Proposal, in order

1. **Compiler: `M<nn>.json` → `presentation/index.html` + `tasks/*.html` + `assessment/*.html`.**
   - Emits the existing shell, tokens and composition classes (`course-module-ui/templates/`,
     `course-module-ux/assets/gb_deck.js`, `gb_run.js`) — no new look.
   - One shared task runtime for the 14 mechanics instead of hand-written grading JS per page;
     emits `data-key` via `gb_key()`.
   - Escape hatch: a screen may reference a hand-made figure/fragment file (SVG schematic, 3D,
     interactive diagram) that the compiler embeds as-is. Do not try to model every figure.
   - Re-runnable: edit the JSON, recompile; never hand-edit the output (mark it "generated").
2. **Generate the course-level files:** `START_HERE*.html`, `COURSE.html`, `_course_shell/course_map.js`,
   `course.json` (`course-factory/knowledge/classroom-system.json:8` says the factory writes them; no script does).
3. **Editor UI** over the same JSON (later). Content only — layout stays the compiler's job.

### Vocabulary the compiler must cover (already defined in the plugin)

- Script kinds: slide, task-slide, activity, self-check, module-check, final (`course-factory/script/GUIDE.md` §1).
- Screen kinds: opener, teaching, activity-launch, practical-run, drill, marking, debrief, summary, check
  (`course-module-ux/build/knowledge/screen-kinds.json`).
- Compositions and blocks: `course-module-ui/references/vocabulary.md` §3–4.
- Task mechanics (14): single_choice, multi_select, read_instrument, order, label_diagram, match,
  categorise, cloze, hotspot, spot_the_hazard, choose_and_justify, set_value, panel_operate, scenario.
- Task-page protocol: `gb-task-done` / `gb-timer` / `gb-team` messages (`classroom-system.json`).

### Validators a compiler makes redundant (or reduces to one self-test)

`check_script_match.py`, `check_navigation.py`, `check_static.py` (links in slides), `verify_course.py`
(structure), `crosscheck_tasks.py`, `check_task_pages.py`, `audit_ui.py`, `check_balance.py`.
**Still needed:** hours, syllabus coverage, `check_slide_text`, visuals/rights, and the browser
`audit_*.js` overflow/composition checks.

### Suggested first slice

Compile Module 1 of the IGF pilot (or one GAS BASIC module, the reference course) for *slide* screens
only, diff against the hand-built deck, then add task mechanics one by one.

## 4 · Bugs found in the pilot (from `course/working_claude/factory-notes.md` §9)

Separate small PRs / issues, independent of the compiler:

1. Last screen conflict: `course-module-ux` `floor.json` wants a hand-off screen after the module check;
   `content_script.py` forbids any screen after it → `check_static.py` always reports 2 findings.
2. `check_static.py` forbids "score" on the check screen, but law L27 says trainees see their score.
3. `check_course_package.py` looks for `gb-task-done` / `gb-timer` only in page text, so a shared task
   JS file fails it. **Must be fixed before the compiler's shared task runtime.**
4. `old_course.py inventory` reports "0 slides" for an old course that exists only in a knowledge base.
5. `kb_tool.py sources` overwrites `kb_sources.json` per knowledge base — only the last survives.
6. Runtime audits with the browser pane hidden measure 3D labels before `requestAnimationFrame` → false collisions.

Also noted: `novikontas-course-start` / `COURSE_START.json` were not wired into the pilot (to do before Module 2).

## 5 · Open questions for Raivis

- Is a generated deck acceptable as the canonical product, with hand-made figures as embedded files?
- Where should the compiler live — a new `course-factory/compile/` lane, or inside `content_script.py`?
- Should the 31 vs 20 gap (slides added only on the HTML side) become script screens, i.e. must
  every delivered slide exist in the script?
- Does the tablet importer (`course-tablet-publisher/vendor/package-core.mjs`) need anything new
  for a shared task runtime file?

## 6 · How to work on this

- Repo: **factory-mjaso** (this clone). Not `novikontas-training-app` — that is the Android app; touch it
  only if the tablet importer needs a change.
- Read first: `00_READ_ME_FIRST.md`, `_claude/CONTEXT.md`, `docs/PHASE5_GAP_REPORT.md`,
  `plugin/skills/course-factory/script/GUIDE.md`.
- Etiquette: never commit to `main`. New branch → commit → push → PR for Raivis. Bump
  `plugin.json` version when it should reach colleagues. Ask Aleksis before pushing or opening a PR.
- Start with a short design proposal (`docs/PROPOSAL_SCRIPT_COMPILER.md`) as its own PR before code,
  so Raivis can agree to the direction.
