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
| Work for one module | about 1,700 messages in the build session for one 40-minute module; the course has 16 |
| Two copies drift | `M01.json` has 20 screens; the built deck has 31 `.slide` sections, 11 of them carry `data-script`; 11 of 20 script titles appear verbatim in the HTML |
| Every fix made twice | `FEEDBACK_LOG.md` rows 4–17: each wording fix applied to the JSON, then again to the HTML |
| Layout fixed per module | row 18, "the text is cut off" — fixed by hand in this module only; the next module can repeat it |
| Nothing builds the deck | `content_script.py` builds the review page (`render_html`, :936) and the Word file (`render_docx`, :1129); `gb_key()` (:450) only checks keys. `gb_shell.html:4` says "Paste this. Fill the CAPITALISED placeholders." |
| Rules loaded per module | `PHASE5_GAP_REPORT.md` §3, point 5 — about 80,000 tokens of rules before the first slide; 8 modules ≈ 640,000 |

The rules that cost the most to load are the ones about *how to write the HTML* — the shell, the
composition classes, the task-page protocol, the classroom folder rules. A compiler holds them in
code once, so a module session needs only the script lane and the picture work.

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
  The look stays where it is; the compiler only stops it being retyped.
- **a figure maker.** A schematic, a 3D model, an animation or an interactive diagram is still made by
  hand or by `course-visuals` / `image-director`, as today. The script names the file
  (`"figure": "assets/m01_tank_cutaway.html"`) and the compiler places it as it is. It does not try to
  describe every figure in JSON.
- **a content writer.** Nothing that is not in the approved script appears on a trainee-facing screen.
  The content lock (L18, L29) gets stronger, not weaker.

### The one shared task file

Today each task page carries its own grading code. The compiler would ship **one** file that knows the
14 ways of answering (`single_choice` … `scenario`), the task-page states (`course-task-ux` §0, L42),
`gb-task-done` / `gb-timer` / `gb-team` (`classroom-system.json`) and answer keys as `data-key`
(`gb_key()`, never readable). Each task page is then only its questions as data.

Where it lives: copied into each module (`moduleNN/assets/gb_task.js`) and proved identical by hash, the
same way `design_system.py` does for the style files — so every module stays a complete folder (L43).
`_course_shell/` would also be allowed by the classroom rules, but would tie a module to its course.

## 4 · What changes in the script

As little as possible. Today's script already holds the words, kinds, sets, mechanics, answers, picture
kind, layout (`split`, `visual_wide`, `visual_full`) and minutes. Likely additions, all optional:

- `"figure"` — the hand-made figure file for a slide or a hands-on task (hotspot areas, label points,
  panel controls are already in `answer`; their coordinates would go beside the figure).
- `"composition"` — only where `layout` is not enough to pick the composition class.
- screens the deck has but the script does not (opener, section dividers, the hand-off screen) —
  either generated from the module's data or added as script screens; see question 3 below.

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
| 2 | Compiler, instructor-tablet screens only: `slide`, `task-slide`, `activity` → `presentation/index.html` | compile IGF Module 1 into a scratch folder; compare with the hand-built deck screen by screen; `check_script_match.py` passes on 20 of 20; `audit_*.js` in the browser |
| 3 | The shared task file, ways of answering added a few at a time — choose / read first, then order / match / sort / gap-fill, then the picture tasks, then set-value / panel / scenario | per batch: `check_task_pages.py`, `check_course_package.py` with the importer, the "never used a tablet" walkthrough (L42) |
| 4 | Course files: `COURSE.html`, `_course_shell/course_map.js`, `course.json`, start pages — `classroom-system.json:8` says the factory writes them; no script does yet | the classroom importer |
| 5 | Wire it into the build order and the module agents: they load the script lane and the picture lanes, not the HTML rules | token count before and after on one module |
| later | The editor — content only; layout stays the compiler's | separate proposal |

One minor version per step that reaches colleagues; the owner reviews each PR.

## 7 · Risks

- **A generated deck may look plainer than a hand-tuned one.** Answer: the compiler uses the same
  composition classes, and a slide that needs something special uses a figure file. Step 2's
  side-by-side comparison shows it before anything else is built on it.
- **Some hand-built slides have no script screen** (11 of 31 in the pilot). If they matter, they must
  become script screens or generated screens — otherwise they disappear.
- **The tablet.** A shared task file is new for the importer (`course-tablet-publisher/vendor/package-core.mjs`)
  and the app's WebView. Step 1 and the importer run in step 3 prove it on this computer; the real-tablet
  test stays the owner's (L39).
- **The migrated skills' rules came from real failures.** The compiler implements them; it does not
  rewrite or drop any. Where a rule cannot be expressed in code it stays in its lane.

## 8 · Questions for Raivis

1. Is a generated deck acceptable as the delivered product, with hand-made figures as embedded files?
2. Where should the compiler live — a new `course-factory/compile/` lane (my suggestion: it keeps
   `content_script.py` for writing and approving, and the new lane for building), or inside
   `content_script.py`?
3. Must every delivered slide exist in the script? (Opener, dividers and the hand-off screen could be
   generated from the module's data instead.)
4. Does the classroom importer need anything for a shared task script file inside a module?
5. Once the compiler is proven, may the checks in §5 that pass by construction move from "run every
   build" to "run in the compiler's own tests"?

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
