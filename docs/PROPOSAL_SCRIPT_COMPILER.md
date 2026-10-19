# Proposal — build the module from its approved script (the script compiler)

*2026-10-15 · Aleksis Vējš, with Claude · for Raivis to agree the direction before any code.
Plugin `course-factory` 2.24.0. This document changes no rule and no file in the plugin.*

---

## 1 · In one paragraph

Today every module is written twice. First the content script (`working_claude/script/M<nn>.json`,
Stage 3, L29), which the operator corrects and approves word for word. Then the same words again,
by hand, as HTML — the deck, every task page, the start pages — and `check_script_match.py` proves
afterwards that the second copy did not drift from the first. **Proposal: a script that builds the
module's HTML from the approved script**, using the factory's own shell, style files and engines.
The model writes only the script (a JSON file — plain text, opens in Notepad); the HTML is generated, never edited by hand. A wording fix is made once,
in the script, and the module is rebuilt. Later, a small **editor** on the same JSON lets an
instructor fix wording or reorder screens without an AI session.

## 2 · Why — what the pilot showed

Checked on 2026-10-15 in the IGF Basic pilot (`Kursi\Drošības pamatkurss\course\`, Module 1) and in
the plugin:

| | |
|---|---|
| Work for one module | the build session for one 40-minute module: 547 model calls (main session and 6 helpers), 24 messages from the operator, about 3.4 hours of model work; the course has 16 modules |
| The words are typed twice | `M01.json` has 20 screens: 11 for the instructor tablet and 9 questions. The deck has exactly those 11 slides, each marked with its script id and every title word for word — correct, but typed a second time by hand and then proved by `check_script_match.py` |
| Late fixes go in two places | `FEEDBACK_LOG.md` rows 20–22 changed the script after the module was built (row 18 is already Stage 4), so the deck had to be changed to match |
| Layout fixed per module | row 18: a drawing spilled over the top of slide 7; fixed in this module's own style file (`m01.css`, edited 25 times in the session) — the next module can repeat it |
| Nothing builds the deck | `content_script.py` builds the review page (`render_html`, :936) and the Word file (`render_docx`, :1129); `gb_key()` (:450) only checks keys. `gb_shell.html:4` says "Paste this. Fill the CAPITALISED placeholders." |
| Rules loaded per module | `PHASE5_GAP_REPORT.md` §3, point 5 — about 80,000 tokens of rules before the first slide; 8 modules ≈ 640,000 |

The rules that cost the most to load are the ones about *how to write the HTML* — the shell, the
composition classes, the task-page protocol, the classroom folder rules. A compiler holds them in
code once, so a module session needs only the script lane and the picture work.

### Measured: how much of the pilot session was HTML work

The pilot's Module 1 session (`8451f44f`, 2026-10-14, with its 6 helper agents) sorted call by call
by what each call touched. "Context" is the text the model re-reads on every call — the main cost.

| Work | Calls | Model output | Context read | Time |
|---|---|---|---|---|
| Writing, reading and checking the module's HTML, CSS and task code | 17 % | 39 % | 18 % | 13 % |
| Looking at the deck and task pages in the browser (layout, overflow, clicks) | 28 % | 6 % | 32 % | 11 % |
| **HTML work together** | **45 %** | **45 %** | **50 %** | **23 %** |
| Pictures, 3D model and its checks | 20 % | 18 % | 19 % | 10 % |
| Intake and architecture (Stages 1–2, same session) | 11 % | 13 % | 5 % | 9 % |
| Script, notes, replies to the operator, other | 24 % | 23 % | 26 % | 58 % |

**Part of the first row is drawing, not HTML.** A third of what was written into the module's pages,
style files and task code was figure drawing typed straight into the page — 23 drawings make up 57 %
of the deck file, and about 45 % of each task page. A compiler does not draw them; they move into figure files and are
still made by hand.

What this means for the saving:

- **Gone with a compiler:** the rest of the first row — about 12 % of the cost (text re-read) and a
  quarter of the writing.
- **Smaller:** the browser row. The layout checks still run once per compiled module, but the
  fix–reload–measure loops (most of those 155 calls) happen once, in the compiler.
- So the module build should cost **between an eighth and two-fifths less, most likely about a
  quarter**. Modules 2–16 have no intake or architecture work, so their share is higher than in
  Module 1.
- In clock time the gain is smaller: the session ran 2 h 40 min, so about **10–20 % faster** —
  15 to 30 minutes a module, 4 to 8 hours over the other 15. Replies, pictures and the operator's
  own time do not change.
- The bigger gain may be the **same look in every module** (§3a) and fixing a layout bug once.
- Not measured here: the rules loaded per module (row above), which the compiler also reduces.

Method: a script sorted each model call by the files and tools it used; module CSS and task code
count as HTML work, figures and the 3D model as pictures. Time counts gaps of up to 5 minutes; longer
gaps are the operator's time and are not counted.

## 3 · What it is — and what it is not

**It is** a new step after approval:

```
python scripts/compile_module.py <course> --module 1
```

| Reads | Writes (in `course\modules\moduleNN\`, L45) |
|---|---|
| the approved `working_claude/script/M01.json` | `presentation/index.html` — every `slide`, `task-slide`, `activity`, with `data-script` / `data-script-field`, `data-task-href`, `data-cue`, `data-visual` |
| the factory's shell and style files (`course-module-ui/templates/`) | `tasks/*.html` — one page per self-check set, team task (TT) and hands-on task |
| `gb_deck.js`, `gb_run.js` (`course-module-ux/assets/`) | `assessment/*.html` — the module check (PASSED / NOT PASSED, never graded, L27) |
| hand-made figure files the script points to | `START_HERE.html`, `START_HERE_EXTENDED.html` (L43) |
| | one shared task file for the 14 ways of answering (L38), copied into the module like the style files |

Every generated file says at the top that it is generated, from which script and which plugin
version. Running it again on the same script gives the same files.

**It is not:**

- **a new look.** It emits the existing shell, tokens and composition classes (L17, `course-module-ui`).
  The look stays where it is; the compiler only stops it being retyped — and makes it the same in
  every module (§3a).
- **a figure maker.** A schematic, a 3D model, an animation or an interactive diagram is still made by
  hand or by `course-visuals` / `image-director`, as today. The script names the file
  (`"figure": "assets/m01_tank_cutaway.html"`) and the compiler places it as it is. It does not try to
  describe every figure in JSON.
- **a content writer.** Nothing that is not in the approved script appears on a trainee-facing screen.
  The content lock (L18, L29) gets stronger, not weaker.

### The one shared task file

Today each module writes its own task code. In the pilot, `m01_tasks.js` (21 KB) and `m01_tasks.css`
(13 KB) were written by hand for Module 1's two task pages; the factory's own shared task ending
(`task_complete.js`) and keyboard helper (`kbd_escape.js`) were copied into the module but no page
loads them. Module 2 would write its own again. The compiler would ship **one** file that knows the
14 ways of answering (`single_choice` … `scenario`), the task-page states (`course-task-ux` §0, L42),
`gb-task-done` / `gb-timer` / `gb-team` (`classroom-system.json`) and answer keys as `data-key`
(`gb_key()`, never readable). Each task page is then only its questions as data.

Where it lives: copied into each module (`moduleNN/assets/gb_task.js`) and proved identical by hash, the
same way `design_system.py` does for the style files — so every module stays a complete folder (L43).
`_course_shell/` would also be allowed by the classroom rules, but would tie a module to its course.

## 3a · The same look in every module

**Today the look is only partly shared.** Every page loads the factory's style files (`gb_tokens`,
`gb_shell`, `gb_compose`, `gb_page`, `gb_task`). But the pilot module adds two style files of its own:

- `m01.css` (12.5 KB) — the colours of its drawings, and also its own slide-text layout
  (`.m01-copy`) and a change to the shared two-column layout (`.slide-body.two-col`) for this module only;
- `m01_tasks.css` (13 KB) — a complete task-page design of its own (screens, options, the answer dock,
  feedback), on top of the factory's `gb_task.css`.

Each new module written by hand does the same, so sixteen modules can end up with sixteen slightly
different slide-text layouts and task screens.

**With the compiler:** the deck and the task pages are built only from the factory's shared classes,
so every module, in every course, has the same slide layouts and the same task screens. A module's
own style file is kept **for its drawings only** (colours and labels inside a figure). When a module
needs something the shared files lack — as Module 1 needed `.m01-copy` — it is added once to the
shared files, and every module gets it on the next build. The compiler can warn when a module's own
style file touches a shared class.

This needs one decision (question 6): which of `m01.css` and `m01_tasks.css` becomes part of the
factory's shared look, and which goes.

## 4 · What changes in the script

**Nothing** — decided while building step 2 (2.25.0). Today's script already holds the words, kinds,
sets, mechanics, answers, picture kind, layout (`split`, `visual_wide`, `visual_full`) and minutes.
Delivery details go into a **build sheet** beside it (`working_claude\script\M01.build.json`), because
any change to the script itself undoes the operator's approval:

- `"figure"` — the picture file of each slide. Drawings are source, in `working_claude\figures\M01\`
  (an `.html` drawing in the module folder would ship to the tablets as a page); photographs ship in
  `assets\img\`. For a hotspot, label or panel task the figure names its areas, and the compiler links
  each line of `answer` to the area with the same name — the script itself holds no coordinates.
- `"composition"` — only where `layout` is not enough to pick the composition class; `"dark"`.
- the module's drawing styles and figure scripts, the landing line, the footer title.
- screens a future deck might need that the script does not have (a section divider, the hand-off
  screen after the module check) — either generated from the module's data or added as script
  screens; see question 3 below. The pilot deck has none: every slide is a script screen.

`content_script.py` keeps its checks; a new field is checked the same way.

## 5 · The checks

Nothing is deleted. Some checks prove that a person typed the HTML correctly; on generated HTML they
pass by construction. They keep running on the compiled output until the owner decides otherwise, so
the compiler is tested by the same checks that test a hand-built module today:

| Check | On compiled output |
|---|---|
| `check_script_match.py`, `crosscheck_tasks.py`, `check_task_pages.py`, `check_navigation.py`, `check_static.py`, `verify_course.py`, `audit_ui.py`, `check_balance.py` | should pass every time — a failure is a compiler bug, fixed once for every course |
| hours, programme coverage, `check_slide_text.py`, visuals and rights, `check_course_package.py` with the classroom's own importer, the browser `audit_*.js` overflow and composition checks | still needed exactly as today — they check content, pictures and the real layout, which a compiler does not guarantee |

## 6 · Order of work — small steps, each one tested

| Step | What | Proof |
|---|---|---|
| 0 | This proposal | Raivis agrees the direction |
| 1 | `check_course_package.py` finds `gb-task-done` / `gb-timer` also in a task page's shared script file, not only in the page text (today `:313`, `:321` read the page only) | its tests, plus a fixture page that uses a shared file |
| 2 | Compiler, instructor-tablet screens only: `slide`, `task-slide`, `activity` → `presentation/index.html`; Module 1's deck drawings moved into figure files; what `m01.css` styles beyond its drawings added to the shared files, as agreed in question 6 | compile IGF Module 1 into a scratch folder; compare with the hand-built deck screen by screen; `check_script_match.py` passes on all 11 slides; `audit_*.js` in the browser |
| 3 | The shared task file, ways of answering added a few at a time — choose / read first, then order / match / sort / gap-fill, then the picture tasks, then set-value / panel / scenario | per batch: `check_task_pages.py`, `check_course_package.py` with the importer, the "never used a tablet" walkthrough (L42) |
| 4 | Course files: `COURSE.html`, `_course_shell/course_map.js`, `course.json`, start pages — `classroom-system.json:8` says the factory writes them; no script does yet | the classroom importer |
| 5 | Wire it into the build order and the module agents: they load the script lane and the picture lanes, not the HTML rules | token count before and after on one module |
| later | The editor — content only; layout stays the compiler's | separate proposal |

One minor version per step that reaches colleagues; the owner reviews each PR.

**Where it stands (2026-10-16, 2.37.0).** Steps 1-3 are built (2.25.0-2.36.0; step 3 has 9 of the 19 ways of
answering). Step 4: `compile/scripts/compile_course.py` writes `COURSE.html`, `course_map.js` and every module's two
start pages; on a copy of the IGF pilot (Modules 1-3) `check_course_package.py` and the classroom's importer find
nothing wrong with them, and the course keeps its ID ("basic-training-for-service-on-ships-subject-to-the-igf-code").
`course.json` is not written - in the classroom's folder layout its importer makes it. Step 5: `build-order.json`
steps 8, 10, 11, 15, the orchestration guide and `build_course.js` send a module agent through the script, then the
compiler. Measured as §3 of `PHASE5_GAP_REPORT.md` did (size ÷ 4):

| A module agent loads | Before (hand-built) | After (compiled) |
|---|---|---|
| course-factory SKILL + build order + script lane + picture lanes (course-visuals, figure kit) | ≈ 35,000 | ≈ 35,000 |
| HTML rules: course-module-ux (router, build guide, screen kinds, audience split, floor, classroom system), course-module-ui (router, vocabulary, anatomy, tokens, frame), course-task-ux (router, media-and-tasks) | ≈ 45,800 | - |
| the compile lane (`compile/GUIDE.md`) | - | ≈ 3,600 |
| **rules before the first slide** | **≈ 80,800** | **≈ 38,500 (−52 %)** |

And what it writes: the IGF pilot's Modules 1-3 have 80, 163 and 129 KB of deck and task-page HTML; compiled, the
module agent writes a build sheet of 3-5 KB instead (plus its figures, 41-95 KB, which it drew either way). Eight
modules: about 340,000 tokens of rules saved before any content.

## 7 · Risks

- **A generated deck may look plainer than a hand-tuned one.** Answer: the compiler uses the same
  composition classes, and a slide that needs something special uses a figure file. Step 2's
  side-by-side comparison shows it before anything else is built on it.
- **A slide that is not in the script would not be built.** In the pilot every slide is a script
  screen, so nothing is lost; a later module that wants an extra slide adds it to the script.
- **The tablet.** A shared task file is new for the importer (`course-tablet-publisher/vendor/package-core.mjs`)
  and the app's WebView. Step 1 and the importer run in step 3 prove it on this computer; the real-tablet
  test stays the owner's (L39).
- **Moving the drawings out of the pages is real work.** Module 1 has 23 drawings in its deck and
  more in its task pages; each becomes a file. Step 2 does this for Module 1 and shows how long it took.
- **The shared look must grow.** What Module 1 styled for itself has to be added to the shared
  files, or the compiled deck looks plainer (§3a, question 6).
- **The migrated skills' rules came from real failures.** The compiler implements them; it does not
  rewrite or drop any. Where a rule cannot be expressed in code it stays in its lane.

## 8 · Questions for Raivis

1. Is a generated deck acceptable as the delivered product, with hand-made figures as embedded files?
2. Where should the compiler live — a new `course-factory/compile/` lane (my suggestion: it keeps
   `content_script.py` for writing and approving, and the new lane for building), or inside
   `content_script.py`?
3. Must every delivered slide exist in the script? (A divider or the hand-off screen could be
   generated from the module's data instead.)
4. Does the classroom importer need anything for a shared task script file inside a module?
5. Once the compiler is proven, may the checks in §5 that pass by construction move from "run every
   build" to "run in the compiler's own tests"?
6. May a module's own style file be limited to its drawings, with slide text and task screens styled
   only by the shared files? If yes: which parts of Module 1's `m01.css` and `m01_tasks.css` become
   shared, and which go?

## 9 · Not part of this — separate small fixes found in the pilot

From `Kursi\Drošības pamatkurss\course\working_claude\factory-notes.md` §9 (opens in any text
editor). Nothing to do for the reader: the factory fixes each one in its own small PR, and Raivis
sees it as a separate review.

1. The last screen: `course-module-ux` `floor.json` wants a hand-off screen after the module check;
   `content_script.py` forbids any screen after it, so `check_static.py` always reports 2 findings.
2. `check_static.py` forbids "score" on the check screen, but L27 says trainees see their own score.
3. `check_course_package.py` reads `gb-task-done` / `gb-timer` only in the page text — step 1 above.
4. `old_course.py inventory` reports "0 slides" for an old course that exists only in a knowledge base.
5. `kb_tool.py sources` overwrites `kb_sources.json` for each knowledge base; only the last survives.
6. Browser audits with the pane hidden measure 3D labels before the first frame, giving false collisions.

Also: `novikontas-course-start` / `COURSE_START.json` were not wired into the pilot; to do before Module 2.
