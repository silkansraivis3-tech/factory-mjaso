# Working context — NOVIKONTAS Course Factory

For the next Claude session. Read this before touching anything in this repository.

**Status 2026-10-15: `course-factory` 2.32.0 + `nano-banana` 1.2.0. The script-compiler branch merged with main 2.31.0 - its laws renumbered L48-L54 → L52-L58 (main's L48-L51 kept). The deck's own Next walks a figure's steps (`gb_deck.js` hook `step`), and `audit_drive.js` measures every step. L51 every picture opens full screen (`gb_zoom.js`) and every module closes with the same animated recap before its module check; L26 revised - the design is the person's after one warning, their choice recorded (`design_choices.py`) and obeyed by every check; the material keeps its four hard limits. L50 a fix is not a build - a new fix mode: find every place across the modules at once, one list, one yes, change, one check (`fix/GUIDE.md`, `scripts/fix.py`, `scripts/measure_slides.py`); the full sign-off stays for builds, retrofits and handover. Five new tablet tasks for the higher Bloom levels (step 4 of the 20/80 plan - the plan's four steps are done). L49 20 / 80 in class: measured (2.26.0), and the factory proposes theory-as-activity per sub-topic for the operator to keep or strike (2.27.0) - steps 1-3 of the owner's 20/80 plan; step 4, new creative task types, not built. L48 the Bloom map (part 1 of the owner's Bloom plan; parts 2-3 - floors as rules, new task types for Analyse-Create - not built). Phase 5 in progress — steps 0–5 done, and redone after the owner's review of the example pages (L34–L36); next is the pilot, Stages 1–3.**

**From the script-compiler branch (its own 2.25.0-2.27.0, merged as 2.32.0):** Figures now come from the figure kit (L55, `course-visuals/kit/`); every photograph opens in a panel (L56); a drawing carries the real photos of what it shows (L57). Phase 5 in progress — steps 0–5 done, and redone after the owner's review of the example pages (L34–L36); the pilot (IGF Basic) is at Module 2. The script compiler (`docs/PROPOSAL_SCRIPT_COMPILER.md`, agreed) is being built: the deck in 2.25.0; task pages, module check and start pages next.**
Phase 5 upgrades the factory to the owner's six-stage production process (intake → architecture
STOP → word-for-word content script STOP → pilot Module 1 with five roles → remaining modules →
final assessment and handover). The owner's decision record, the gap analysis and the approved
step plan are in **`docs/PHASE5_GAP_REPORT.md`** — read it before changing anything. Where the
owner's Phase 5 decisions conflict with an older rule, the Phase 5 decision wins and is recorded
in the owning skill and in `docs/FACTORY_LAWS.md`.

Approved order: step 0 (clean-up, **done in 2.10.1**) → step 11 (lighter loading, **done in
2.11.0**) → step 11b (style files copied, not read, **done in 2.11.1**) → step 11c (the factory's own style
files pass the strict look check, **done in 2.11.2**) → step 1 (the owner's decisions as laws
L26–L33, **done in 2.12.0**) → step 2 (intake + knowledge base, **done in 2.13.0**; `find` in 2.13.1) → step 3 (the course remembers, **done in 2.14.0**) → step 4 (the architecture page, **done in 2.15.0**) → step 5 (the content script, **done in 2.16.0**) →
STOP for the pilot course → Stages 1–3 on it → steps 6–10 → build the pilot Module 1. After every
step: stop, give the owner a short plain summary and the exact commit/push commands.

`claude plugin validate --strict` passes for both plugins and the marketplace; 6 test files,
139 tests, all passing at 2.10.0.

Not built yet: `course-evidence`, the `evidence-retriever` agent, the deterministic hooks,
`resources/engines/`.

### How it got here

| Version | Date | What |
|---|---|---|
| 2.0.0 | 2026-09-10 | Phase 2 — five proven skills migrated from `course-factory` 1.3.0 |
| 2.1.0 | 2026-09-10 | Phase 3 — `course-visuals`, `visual-sourcer`, the asset pipeline |
| 2.2 | 2026-09-11 | Phase 4B — repairs from the ETPB3 pilot |
| 2.3 | 2026-09-11 | Phase 4C — the composition system (`gb_compose.css`, L17) |
| 2.4 | 2026-09-11 | RETROFIT as a first-class mode (L18) |
| 2.5 | 2026-09-11 | figures proven alive (L20), task-page states |
| 2.6 | 2026-09-14 | PREVIEW → APPROVAL → PUBLISH (L21) |
| 2.7 | 2026-09-15 | a slide is not an internal document (L22) |
| 2.8 | 2026-09-15 | the picture comes first (L23); parallel module build |
| 2.9 | 2026-09-15 | a call and a folder; expert edits (L24); plain-language reports (L25) |
| 2.10 | 2026-09-29 | the `nano-banana` plugin as a dependency |
| 2.10.1 | 2026-09-30 | Phase 5 step 0 — stale pointers fixed, one law numbering |
| 2.11.0 | 2026-09-30 | Phase 5 step 11 — the long reasoning in `course-factory` and `course-task-ux` moved (word for word) into `references/`; new detail goes into lanes, never back into a SKILL.md |
| 2.11.1 | 2026-09-30 | Phase 5 step 11b — `course-module-ui/scripts/design_system.py` copies the style files and engines into a module and proves them identical; the model reads `references/vocabulary.md` instead of ~58 KB of CSS |
| 2.11.2 | 2026-09-30 | Phase 5 step 11c — 128 raw colours in four shared style files became file-local named tokens with identical values; the strict look check passes on the factory's own files; look proven unchanged (computed styles and screenshots) |
| 2.12.0 | 2026-09-30 | Phase 5 step 1 — laws L26–L33 (owner's decision record); L26 built out: the operator's request wins, style means brand only, a new **edit** routing mode |
| 2.13.0 | 2026-09-30 | Phase 5 step 2 — intake as one batch of pop-up questions (`knowledge/intake.json`), course type (`knowledge/course-type.json`), and the `kb/` lane: both knowledge-base kinds, exact copies and editions sorted before anything is cited, search packs into the course folder only |
| 2.13.1 | 2026-09-30 | `kb_tool.py find` — every knowledge base in the course folder, its sub-folders and one level up, read-only |
| 2.14.0 | 2026-09-30 | Phase 5 step 3 — the course remembers: `COURSE_STATE.md` at every STOP, `FEEDBACK_LOG.md` for every correction, pattern files shown and approved by the operator before they are saved (`scripts/course_memory.py`); the publisher keeps all of them and `factory-notes.md` off the tablets |
| 2.15.0 | 2026-09-30 | Phase 5 step 4 — the Stage 2 STOP as one page, `ARCHITECTURE_REVIEW.html` (`scripts/make_architecture_page.py`): hours with their programme rows, Main ILOs verbatim, every Sub-ILO beside its programme wording, active learning, practicals, test plan; course text in the course language, the page in the operator's (en / lv / ru) |
| 2.16.0 | 2026-09-30 | Phase 5 step 5 — the Stage 3 content script (`script/GUIDE.md`, `scripts/content_script.py`): every screen word for word in trainee order, a review page and a **Word file** for the operator, corrections shown as an understood list and applied only on confirmation, `check_script_match.py` for the built module. Proved with real Word |
| 2.16.1 | 2026-09-30 | The slide-text check (L22) runs on the content script before approval; its findings head the review page and the Word file, and block approval unless the operator approves despite them. Fixed: two corrections applied in the same second no longer leave a pending list behind |
| 2.17.0 | 2026-09-30 | The owner's review of the example pages - **L34** one module per programme topic, the final assessment last and alone (GAS Basic: 22 + 1); **L35** two tablets - slides on the instructor's, tasks only on the trainee's, opened with OPEN TASK, no task list, the trainee's own score on every self-check and module check; **L36** enough theory before any task (`knowledge/theory-rules.json`, checked on the script). Architecture page and content script rebuilt; examples remade from the real programme |
| 2.18.0 | 2026-09-30 | **L37** every slide leaves room for a named picture - kind, what it shows, layout, who makes it (factory / image-video generator / sources / Novikontas photo, film or phone 3D scan / outside help); **L38** 14 ways of answering, none typing, with variety floors and a hands-on question in every module; **English only** - COURSE_LANGUAGE is never asked. `knowledge/media-and-tasks.json` |
| 2.37.1 | 2026-10-16 | Two compiler fixes found building IGF Module 4: a script slide with `"recap": true` is built in the shared closing design (L51 - before, it came out as a plain theory slide and failed `check_course_package`); a compiled "choose all" question carries `data-multi="1"`, so `gb_answer.js` keeps every tap (before, only the last tap counted and a fully right answer scored wrong - every module compiled since 2.34.0: rebuild its task pages) |
| 2.37.0 | 2026-10-16 | Compiler proposal steps 4-5. **The course's own pages built, never typed**: `compile/scripts/compile_course.py` writes `COURSE.html`, `_course_shell/course_map.js` and every module's `START_HERE.html` / `START_HERE_EXTENDED.html` from the approved architecture, scripts and built decks; the course title (the classroom's course ID) never changes without `--retitle`; `course.json` left to the importer. **Module agents compile**: `build-order.json` steps 8/10/11/15, `orchestration/GUIDE.md` and `build_course.js` - script, approval, build sheet, compile; the HTML rules are no longer loaded (≈ 80,800 → 38,500 tokens of rules per module agent, measured). `test_compile_course.py` 21 checks |
| 2.38.0 | 2026-10-16 | **Every way of answering compiled** - no trainee task page is made by hand any more. `task_pages.py` builds the ten that were left (cloze, choose_and_justify, scenario, set_value, find_the_fault, spot_the_error, build_the_plan, timeline, compare, panel_operate); the one engine `gb_answer.js` grades a question of one or more parts (a scenario's steps, the incident's order then its stop point), a dial (one key per accepted step), cards that belong or not (`data-place`), a panel whose valves and pumps the figure kit draws. Places on a drawing may be a straight-line path in a `translate()`d group. Checkers fixed with tests: `check_script_match` (a panel's other positions, `data-state`), `check_task_pages` (`data-kit="#id"`, ids inside `svg.taskfig`), `check_course_package` (`data-no-zoom` is no picture). IGF pilot copy: every M01-M03 set compiled, word-for-word match. `test_task_engine.py` drives the page in headless Chrome |
| 2.39.0 | 2026-10-16 | **Team task pages compiled** (`classroom-system.json` `team_task`): a task slide with `"team"` gets `task-mode` / `task-roles` / `task-scope` metas on its page beside the slide's `data-mode` / `data-team-size` / `data-roles`; the engine shows the team and the trainee's role from `gb-team`, runs alone when none comes within ~2 s, hands in one answer with `scope: 'team'` (first tablet to finish, any team size, no role locks anyone out) or everyone's own (`member`); other members' pages show "Handed in by ... for Team A" on `gb-team-done` - **a factory proposal the classroom app must confirm**. Tests: `test_compile_module.py` team part, `test_task_engine.py` four team cases in Chrome |
| 2.39.1 | 2026-10-16 | The 1280 × 800 walkthrough of the new task pages (IGF pilot copy + fixture), fixed: the engine wrote `.className` on a drawing's SVG element that carried `data-for` and stopped (label question, M02 SC2) - classes now go through the attribute and only the compare table's `data-for` is read (regression test in `test_task_engine.py`); compare's row names were navy on navy and its figures 50 px high; the stop point read as an error (red) - now green, the empty bank hidden; find the fault's picture sits beside the symptoms so the cards fit; the feedback is brought into view above the dock; feedback and intro text 17 / 20 px (were 14.8 px through `gb_page.css` `p`); the why of a wrong line has full contrast |
| 2.40.0 | 2026-10-16 | **Task screens and start pages in Latvian and Russian** (L19 COURSE_LANGUAGE): `task_pages.py` and `compile_course.py` WORDS and the engine's `LANG` (by `<html lang>`) in en / lv / ru, the whole page in one language; **PROVISIONAL** - every word listed in `compile/TRANSLATIONS_REVIEW.md` for a native speaker; any other language reported (exit 1), never a silent fall-back. `compile_module.lang_code`: "Latvian" is lv (the deck, task pages and start pages said "la"); a title in Latvian or Russian gives a plain-letter file name (`sc1_varsti.html`, was `sc1_v_rsti.html`). On screen PASSED / NOT PASSED in the language, the classroom still gets the code. Tests: lv / ru / Norwegian fixtures in `test_compile_module.py` and `test_compile_course.py`, a Latvian page driven in Chrome (decimal comma) |
| 2.41.0 | 2026-10-16 | **The deck's own words in Latvian and Russian** (L19): `gb_deck.js` `LANG` (by `<html lang>`, `GBDeck.init({text})` still overrides) puts Next, Back, All screens, the instructor cue, Start, the overview and the landing hint in the page's language on the chrome copied from `gb_shell.html`; the compiler stops passing English words to the engine and writes the landing card's chips in the course language (`compile_module.py` LANDING), any other language reported (exit 1). **PROVISIONAL**, in `compile/TRANSLATIONS_REVIEW.md` §4-5. Test: a Latvian deck driven in Chrome (`test_task_engine.py`) |
| 2.33.0 | 2026-10-15 | **One picture viewer** (operator): L51's `gb_zoom.js` is the only one - compiled decks load it too, and `gb_photo.js`/`.css` (L56's panel of 2.27.0) are retired. `gb_zoom.js` gains L56's explanation: full screen shows a photo's record under it (`data-name`, `data-about`, `data-credit` → `.gbz-record`), a full-screen photo slide opens on a tap of its bare picture and has the ⤢ button (`.gbz-photo`). L56 is now the content rule (description + credit onto every photo, unasked). The 2.32.1 "AI-generated illustration" label is removed entirely (operator): a generated picture keeps its record but shows no credit and no label; it is still never an L57 thumbnail. `.photo-strip` styles moved to `gb_compose.css` 16. Still open: L51's recap slide in IGF M01–M03 (script content), and `gb_zoom` on hand-built task/check pages |
| 2.32.1 | 2026-10-15 | **L56 (4)** a picture made by an image model is never called a photograph: a `_photo_meta.json` record with `"generated": true` and `"generator"` makes the compiler write `data-generated`, the credit "AI-generated illustration · <model>" and an inset caption that leads with it; `gb_photo.js` heads the panel "AI-generated illustration" (button "Illustration" on a photo slide); L57 never places one as a thumbnail. First use: IGF M01 s04's nano-banana tank in its fuel storage hold, until a real photo is cleared. Still open from 2.32.0: the package check's L51 findings on compiled decks (`gb_zoom`, recap slide) |
| 2.32.0 | 2026-10-15 | The script-compiler branch merged with main 2.31.0 (Aleksis). main's L48-L51 stay; the branch's laws move up four - L52 real photos, L53 no empty space, L54 every drawing whole, L55 the figure kit, L56 every photo opens, L57 drawings carry real photos, L58 every photo once (140 references in 29 files). Its releases keep their own numbers below, its MANIFEST sections are §4za-§4zf. **Open for the owner:** two picture viewers now ship - L51 `gb_zoom.js` (every picture full screen) and L56 `gb_photo.js` (a photo's panel, then full screen) |
| 2.31.0 | 2026-10-15 | The deck's own Next walks a figure's steps (Aleksis, from the IGF course M03, where the figures were skipped): `gb_deck.js` takes an optional per-screen hook `step(dir)` asked first by Next, Back, the arrow keys and a swipe - no more per-module copies of this; the corner tag hides on a screen with a header band (it sat on top of it); the current step dot lights on a light slide (`gb_compose.css` specificity); `audit_drive.js` walks and measures every step and fails a slide the deck's Next leaves with steps still to show; regression fixture `measure/scripts/fixtures/deck_steps.html` |
| 2.30.0 | 2026-10-15 | **L51** every picture opens full screen and closes again - one shared viewer `gb_zoom.js` / `gb_zoom.css` on every page with a picture (tap; X, tap outside, Esc, swipe down, Back, next slide close; pinch / + / − zoom; a ⤢ corner button where the trainee answers on the picture); every teaching module closes with one recap slide straight before the module check, "what to take away", 3-6 points, the same animated design (`gb_compose.css` 15), checked on the script (r_ findings) and the package. **L26 revised**: the design (brand, components, layout, animation, recap, viewer, text size, space, 3D share - `knowledge/design-rules.json`) is the person's - one warning with the risk, their way recorded in `STANDARDS.md` by `scripts/design_choices.py` and reported as their choice by `check_course_package.py`, `content_script.py approve` and `design_system.py check`, never changed back; the material keeps four hard limits; every skill says so near its top |
| 2.29.0 | 2026-10-15 | **L50** a fix is not a build (GAS ADVANCED: a module built in 1-1.5 h, a small fix ~30 min, FEEDBACK_LOG #61-#93): a new **fix** mode (`routing.json` `fix_triggers`) reads only `fix/GUIDE.md`, `COURSE_STATE.md` and `STANDARDS.md`; `scripts/fix.py` sweeps every module at once (space / text / overflow / layout measured by `scripts/measure_slides.py` in a hidden Chrome or Edge at 1280 x 800, ~4 s a module; last slide, kind, words), one numbered list, one yes (`propose` / `apply --confirmed` / `approve`, L29 kept), a shared part changed once and copied by `sync-shared` (L43 kept), one check by the kind of change; a course-wide wish becomes a numbered standard in `STANDARDS.md`; thresholds in `knowledge/fix-rules.json` |
| 2.28.0 | 2026-10-15 | **L49 step 4** five new tablet tasks for the higher Bloom levels - find the fault, spot the errors, build the plan, rebuild the incident, compare - none typing: answer forms in `media-and-tasks.json`, levels in `bloom.json`, checked, drawn and matched word for word by `content_script.py` / `check_script_match.py`; how each behaves on the tablet in `course-task-ux` §2a |
| 2.27.0 | 2026-10-15 | **L49 step 3** the factory proposes, per sub-topic, how theory is learned by doing (`knowledge/active-learning.json`, `active/GUIDE.md`); the Stage 2 page shows each with Keep / Strike, the split now and if all kept, and *Copy my choices*; `scripts/active_plan.py` records the operator's decisions, logged in their words; only kept ones are built |
| 2.26.0 | 2026-10-15 | **L49** 20 / 80 in class, the programme unchanged, every theory slide kept: plain theory against active minutes on the Stage 2 page and each Stage 3 review page (`theory-rules.json` split; slides marked `"active"`; theory-as-activity with minutes); L36 amended to ~5-minute cycles, density over plain theory only - suggestions only |
| 2.25.0 | 2026-10-15 | **L48** the Bloom map: `knowledge/bloom.json`, `bloom/GUIDE.md`, `scripts/bloom_map.py` - every ILO's level from its verb (en/lv/ru), every task's from its type or stated level; the Stage 2 page and each Stage 3 review page show the share at Apply or higher, every task below its Sub-ILO and the tablet task types that lift it - suggestions only |
| — | | *Below, down to 2.24.0: the script-compiler branch's own releases - its numbering 2.25.0-2.27.0, made beside main's; merged into main's line as 2.32.0, its MANIFEST sections relabelled §4za-§4zf* |
| 2.27.0 | 2026-10-15 | **L56** every photograph opens, unasked (operator, from Aigars's review of the IGF pilot): `course-module-ux/assets/gb_photo.js` + `.css`, loaded by every compiled deck - tap any photo (slide picture, split, inset, or a photo inside a drawing fragment) → a panel with the photo whole, the slide's title, what it shows (`_photo_meta.json` `description`, written for the trainee) and its credit → full screen; a full-screen photo slide gets a Photo button; Escape unwinds; the deck does not move under it. Ported from the oil/chemical course's definition panel (Modules 6, 10). Compiler writes `data-about`/`data-credit`; a photo without a description is reported at build. IGF M01–M03 recompiled (12 photos). **L57** a drawing of real things carries their real photos, unasked: the compiler finds the things a drawn slide names (line terms with the kit step number, the drawing's labels), matches photos by the new `shows` field in `_photo_meta.json`, and puts them in a `.photo-strip` under the drawing (≤ 4, numbered, opening in the panel); a cleared photo of another module is copied in; real things with no photo are reported and written to `working_claude\PHOTOS_TO_TAKE.md`. **L58** every photograph once in the whole course (operator: "no duplicate images - a different one or none, on all modules"): the compiler compares photos by `url_or_origin` or bytes across every built deck; thumbnails give way, a photo placed by hand twice is reported. Also fixed from the photo session's report: the strip and an "under figure" inset go with the words when the drawing is a self-laid-out 3D fragment (canvas was 0 px), and `gb_compose.css` keeps an inset under a kit figure at inset size |
| 2.26.3 | 2026-10-15 | **L53 inside the figure** (operator, after IGF M01 s04): a figure fills the panel it is shown in - `audit_drawing.js` check 4 EMPTY (≤ 50 % blank, no blank piece > 20 %, judged at the last step too; 1280 / 1024 / 1920); a figure whose steps light the slide's lines goes `two-col` beside them at reading size (no stage + small legend cards; legend text now reading size); every lit line (or the box it heads) is a tap target that plays its step (`kit.js`, `.kit-tap` 44 px). `scale` runs across (`orient: "h"`). Audit sampling off the seam of closed shapes (a false "poke out" at 1920) |
| 2.26.2 | 2026-10-15 | First parts promoted from a course (L55): ga, zone, scale, bands, cylinder, boil_off, gas_cloud, integral_tank from IGF Basic M01/M02 (13 slides rebuilt as kit specs; 5 picture-swap animations → 0). Families 3-6 started (SPEC.md); GALLERY.html shows "Parts added from courses" |
| 2.26.1 | 2026-10-15 | Kit fix from the IGF M01/M02 rework: the step badge grows from r 13 to r 15 and the bilge well's "TT" bubble to r 17, so their label keeps the audit_drawing 4 px clearance at every scale (a "4" failed at 1.0×, every digit at ≈1.1× or below 0.9×) |
| 2.26.0 | 2026-10-15 | **L55** figures come from the figure kit (`course-visuals/kit/`): a `*.kit.json` spec of parts and steps, never a one-off SVG; instruments and piping families built (gallery: M02 s03, s04, s14 rebuilt); a part the kit lacks is made in the module's `assets/kit_parts.js` (`PARTS.md`, `check_kit.py`) and, after the module is complete, promoted into the kit with a merge request (`kit_parts.py promote`); the compiler places kit figures and ships the kit. MANIFEST §4ze |
| 2.25.3 | 2026-10-15 | Pilot Module 2 compiled (scratch copy, its drawings moved out and fixed): words 38/38, classroom Ready, drawings 64 -> 0, deck audit clean, 20/20 composed at 1280x800. Compiler: legend ranges, box_alt, grouped boxes, line hooks for figure scripts, inset under the drawing, aside, figure first, room activity with a drawing, existing task page link. Shared look: stage packing, aside, small-projector rule, a group of small figures as the picture. MANIFEST §4zd |
| 2.25.2 | 2026-10-15 | **L54** every drawing whole and clean: `course-module-ux/measure/scripts/audit_drawing.js` (a part out of its hull/tank/room on the real shape, anything cut off at the frame also in a later step, every label's 4 px safe zone), `assets/gb_fit.js` in every compiled deck (widens a frame a drawing still reaches past, names it); `test_audit_drawing.py` in headless Chrome. Pilot M01: 35 findings -> 0; M02 (hand-built): 64 listed. MANIFEST §4zc |
| 2.25.1 | 2026-10-15 | Compiled decks as good as hand-built (IGF pilot M01: 11/11 slides, text 18.4 px, pictures ~30 % bigger): shared reading column `.copy`, `.box`/`.call`, `.legend`, `.inset`, photo beside the words, bigger figure column, task-slide sign (`gb_compose.css` §13b); bold terms; full CC credit line. **L52** as many real photographs as possible (`v_few_photos`), **L53** no empty space, good padding. MANIFEST §4zb |
| 2.25.0 | 2026-10-15 | **The deck built from the approved script, never typed** - `compile/` lane, `compile_module.py` + a build sheet beside the script (pictures, layouts; not content, so approval stands); shared layouts only; hand edits never overwritten; `check_script_match.py --part`. Proved on the IGF pilot's Module 1 (scratch copy). MANIFEST §4za |
| 2.24.0 | 2026-10-14 | **L47** a generated picture only after the person described it and said yes (about €0.10 each): `scripts/picture_briefs.py` (places, eight questions, answers, prompt, every picture made); `media-and-tasks.json` `generation_brief`; **nano-banana 1.2.0**: `approved_by_user` required, usage log and cost in every result, no auto-retry, agent makes approved pictures once |
| 2.23.0 | 2026-10-12 | The classroom rulebook of 2026-10-12 (pasted by the owner): **team tasks** planned in the content script and checked on slide and page (`data-mode`, `task-mode` / `task-scope`, `gb-team`, `scope: 'team'`); answers in trainee pages marked by `data-key` (gbKey, FNV-1a), never readable; no link into `_` folders; timeout / no-retry notes; files up to 15 MB |
| 2.22.0 | 2026-10-07 | **L46** 3D where it makes sense - at most half of the presentation's teaching slides, at full quality (owner: "don't cut quality"), and smooth on the tablet - speed from how scenes run, never a lesser look: `knowledge/media-and-tasks.json` `three_d` (cap, fits / does not fit, performance budget); `content_script.py` `v_3d_share` must-fix + suggestions; architecture `p_3d_many`; `check_course_package.py` counts built slides by `data-visual` and notes what would lag |
| 2.21.0 | 2026-10-05 | **L45** the course folder `course\modules\` is built to the classroom system's own rules (`knowledge/classroom-system.json`, from `tablet-system-win/COURSE_FACTORY_PROMPT.md`): `module01\presentation\index.html`, task slides with `data-task-href`, notes in `data-cue`, `gb-task-done`, module checks PASSED / NOT PASSED for understanding; `scripts/check_course_package.py` runs the list and the classroom's own importer (vendored, byte-identical) |
| 2.20.0 | 2026-10-02 | **L44** three places in `course\`: `to_review\` (only what the operator checks), `modules\`, `working_claude\` (everything only the factory uses, all kept); every tool writes there; `workspace.py tidy` moves an older course - moved, never deleted |
| 2.19.3 | 2026-10-01 | **L43** every module in its own complete folder `course\modules\M01_<title>\` - START_HERE.html opens the presentation straight away, START_HERE_EXTENDED.html has a button for everything; `scripts/check_module_folder.py` proves it |
| 2.19.2 | 2026-10-01 | **L42** trainee-tablet tasks: modern, exciting, usable by someone who has never held a tablet (`course-task-ux` §0; numbers in `media-and-tasks.json` → `trainee_tablet_experience`) |
| 2.19.1 | 2026-10-01 | Every reply to the operator is human: **Done · Check now · Next**, short points, everyday words about computers, maritime terms unchanged (L25; `SKILL.md` top, `plain-language.json` → `every_reply`, a pointer in every skill) |
| 2.19.0 | 2026-10-01 | **L40** the factory works in `course\` beside the operator's material (`scripts/workspace.py`); **L41** the old course is read whole and is the foundation - every module says what it keeps, modernises and adds (`scripts/old_course.py`); **L33 revised** - every picture in the knowledge base and old course is usable, the internet is searched and downloaded from when something is missing, the download list confirmed once per module |
| 2.18.2 | 2026-09-30 | Confirmed: the slide-text floor did not drop in 2.18.1 (50-150 words a slide unchanged; notes now capped, so the slides carry more of the per-minute floor). Same theory numbers for both course types, by the owner's choice; recorded instead that **a basic course never uses easier names** - professional terms, explained so a new entrant understands (L28, `course-type.json`). Step 6 note below |
| 2.18.1 | 2026-09-30 | Instructor notes short (10-50 words) and written to `instructor_notes/M01_INSTRUCTOR_NOTES.md` for the panel, never on a slide; pictures without a quota - the picture floors became suggestions; **L39** colleagues check the HTML in a browser, the owner tests on the tablet at the end |

---

## Install, and where it lands

```
claude plugin marketplace add silkansraivis3-tech/factory-mjaso
claude plugin install course-factory@novikontas-course-factory
```

| | |
|---|---|
| CLI | 2.1.267, native install at `%USERPROFILE%\.local\bin\claude.exe` |
| Plugin | `course-factory` **2.10.x** + `nano-banana` 1.1.x @ `novikontas-course-factory`, scope user |
| Installed cache | `~/.claude/plugins/cache/novikontas-course-factory/course-factory/<version>/` |
| Colleague instructions | `docs/INSTALL_FOR_COLLEAGUES.md` (authoritative copy) |

**Do not confuse the two binaries.** `%LOCALAPPDATA%\AnthropicClaude\claude.exe` is the desktop app
and has no `plugin` subcommands. The CLI is the one under `.local\bin`.

**Edit the repository, not the installed cache** — the cache is overwritten on update. After a
change: **bump `plugin.json`'s `version`** (Claude Code pins a git plugin to its version string and
will not update without it), push, then `claude plugin marketplace update` and `claude plugin update`.

---

## The six skills

| Skill | Owns |
|---|---|
| `course-factory` | programme, hours law, ILO immutability, build order, coverage, the gate |
| `course-module-ux` | how the delivery works — one page, Start, Next, the screen floor, the run script |
| `course-module-ui` | how a page **looks like a NOVIKONTAS page** — tokens, type, components |
| **`course-visuals`** | **what representation teaches a concept**, and where the asset comes from |
| `course-task-ux` | how a trainee answers or completes |
| `course-tablet-publisher` | publishing to the two terminals and the shared repository |

Agents: **`visual-sourcer`** — isolated-context asset investigation only; **`nano-banana:image-director`**
— generates realistic pictures and short clips. Picture generation goes to `image-director`, never to
a model override (until 2.10.1 four files said `Agent(model: "fable")`, which cannot make a picture).

**Second plugin, `nano-banana`** (`./nano-banana`, 1.0.0, 2026-09-29) — a stdlib-Python MCP server
for Gemini image (Nano Banana) and Veo video generation, the `realistic-visuals` skill and the
`image-director` agent. `course-factory` 2.10.0 declares it as a **dependency**, so it installs with
the factory. It is level 4 *generated illustration* of the `course-visuals` pipeline, never a
replacement for an authored schematic. One shared Gemini key. There is no `userConfig`: on first
use without a key, the server opens a tkinter window (PowerShell/osascript fallback), the user
pastes the key, it is checked, and it is saved to `~/.config/nano-banana/gemini_api_key`. The key
never passes through the chat. **Never commit a key to this public repo.**

The boundary that gets blurred: `course-module-ui` owns the **card as a component**. Using cards as
the *answer to a teaching need* is `course-visuals` failing to name the need. Neither restates the
other, and `course-visuals` deliberately contains no colour, radius, contrast or tap-size rule.

---

## Locations

**The Phase 5 pilot course folder** (owner, 2026-09-30): `C:\Users\raiviss\Desktop\mjaso-factory-test` —
`KNOWLEDGE_BASE` (Course Source Processor, 47 sources), `old_course` (GAS Basic, 16 sections), `source_files`.
**Not started.** It runs after step 5: Stages 1–3 on it, the owner reviews, then steps 6–10, then Module 1 is
built. Its own `COURSE_STATE.md` records the same. **The pilot is a GAS Basic rebuild, and the finished
GAS BASIC course (`Desktop\docling\gas_basic\GAS Basic`) is NOT a source for it** — its modules are not read
for content or visuals, so the pilot proves the new process on its own (owner, 2026-09-30).

**Working rule (owner, 2026-09-30): after every edit, re-read the changed lines to confirm they were saved.**
Several edits made through the shell failed on escaping; each was caught and redone, and a check of the
committed files at 2.13.1 found every step's key change in place (29 of 29).


| | | |
|---|---|---|
| Reference course | `C:\Users\raiviss\Desktop\docling\gas_basic\GAS Basic` | **READ ONLY** |
| Android application | `C:\Users\raiviss\AndroidStudioProjects\NOVIKONTASTraining` | **READ ONLY** |
| Old skill bundle | `C:\Users\raiviss\Desktop\novikontas-course-skills` → `github.com/silkansraivis3-tech/course-factory` | superseded; **read-only, do not delete or archive** (D-1) |
| Legacy skills backup | `Desktop\factory-work\_legacy_personal_skills_backup_2026-09-10` | the removed v1.3.0 personal copies |
| Colleague handover | `Desktop\course-factory-handover` | **repointed at the marketplace in Phase 3**; old scripts retired into `_superseded_2026-09-10/` |
| This repository | `github.com/silkansraivis3-tech/factory-mjaso` | **the only write target** |

The Phase 1 brief gave the reference course path as `docling\gas\_basic\GAS Basic`; the real path is
`docling\gas_basic\GAS Basic`. `Desktop\gas basic` is an older, superseded root — **not** it.

---

## Owner decisions

| | |
|---|---|
| **D-1 · VERIFIED** | `factory-mjaso` supersedes `course-factory`; parity and installation both proven. The old repository is untouched. |
| **D-3 · RESOLVED** | Organisation `novikontas-*` skills are **not** copied in. Use the org skill when installed, otherwise the fallback in `plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`, and record the route in `factory-notes.md` §0. |
| **D-2, D-4, D-5, D-6** | Still open — `docs/COURSE_FACTORY_BLUEPRINT.md` §9. |

---

## Findings

**F-1 · RESOLVED.** `plugin/CLAUDE.md` removed; the laws are now `docs/FACTORY_LAWS.md`, marked as
documentation, each naming its enforcing skill. L12 and L13 gained `course-visuals`. **All
twenty-five laws have an enforcing skill** (L1–L25; `course-factory/SKILL.md` uses the same
L-numbers since 2.10.1). `--strict` passes clean.

**F-2 · STILL OPEN.** `course-module-ux/build/GUIDE.md` §8 and `MANIFEST.md` line 158 say the record
engines live in `gas-basic-module-ux/assets/` "as the only copies". That skill is gone.
Pre-existing; closing it is the `resources/engines/` job.

**F-3 · CLOSED** in Phase 2B — duplicate personal skills removed.

**F-4 · RESOLVED.** The handover installer is retired and repointed at the marketplace; the
authoritative instructions are `docs/INSTALL_FOR_COLLEAGUES.md`.

---

## Rules in force

- The reference course, `source_files/`, the knowledge base, the Android application and the old
  `course-factory` repository are **read-only**. This repository is the only place to write.
- **Migration fidelity outranks tidiness** for the five migrated skills — their rules came from real
  production failures. Do not simplify or reword one; if something must change, make the smallest
  change and document it.
- Never bring the ICS/SIGTTO figures here — six are marked *NOT cleared for issue or publication*.
- Do not duplicate organisation-skill content into the plugin (D-3).
- Do not restore installation into `~/.claude/skills/`.
- The owner commits, publishes and installs. The factory builds and reports.

---

## What has and has not been proved

**Proved, on synthetic fixtures (Phase 3 onward):** the asset hierarchy, provenance and rights
escalation, animation rejection, the figure-alive probe, routing, expert-edit detection, the
slide-text and plain-language checks, the publisher gates — the six test files.

**Proved on real material:** retrofit pilots of ETPB3 / ETPA4 modules (Phases 4B–4C).

**Not proved:** a new course built end to end from a knowledge base. The Phase 5 pilot is that test.
`check_visuals.py` reads only **static** markup — a figure built by JavaScript at runtime is
invisible to it, which is why the human review in `course-visuals/review/GUIDE.md` is not optional.

---

## Next session

**For Phase 5 step 6 (owner, 2026-09-30):** check **read-only** that the tablet app records final-assessment results
correctly for every new answer type (all fourteen ways of answering, L38 - including multiple right answers, order,
matching, sorting, set-a-value within a tolerance, panel end states and scenario steps), and list for the owner any app
change needed. The app is not edited (L21, Q1); the owner applies the change list. Build every task screen to
`course-task-ux` §0 (L42): the *try the tablet* first screen, tap-and-drag only with tap-then-tap, the once-only
gesture hint, 56 px controls, instant feedback, the animated score ring - and run the *never used a tablet*
walkthrough in a browser. Build every module into its own complete folder to the classroom's rules (L43, L45) and run
`scripts/check_course_package.py` - it ends with the classroom's own importer; a course is handed over only when both pass. The real-tablet touch test is the
owner's, at the end (L39).

Continue the Phase 5 step plan in `docs/PHASE5_GAP_REPORT.md` §4, in the owner's approved order
(above). The owner's answers to Q1–Q5 and the approved order are in that report's **§6** — they
override the §4 proposals where they differ.
