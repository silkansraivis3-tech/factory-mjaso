# Audit — Raivis's six complaints (2026-11-25, factory 2.137.8)

Read-only. Code traced in `plugin/skills/`; measured on the four built courses in
`C:\Users\aleksisv\Desktop\Kursi` (Project Management, Information Technology, Drošības pamatkurss, IGF Advanced).
Key claims re-checked by hand. Paths below are relative to `plugin/skills/`.

| # | Complaint | Verdict | Size |
|---|---|---|---|
| 1 | Photo in the wrong-shaped layout, bad fit | **Confirmed, systemic** | 205 of 243 photos are wide; most go in a near-square column and use ~66 % of it |
| 2 | One slide cut into 2-3 tiny slides | **Partly** — real, but milder than described | 0 slides under 25 words; forced 2-part splits and "b" slides exist |
| 3 | Expert changes reach the work | **Gap confirmed in code**, never exercised on real data | No editor-mode change exists yet in any course |
| 4 | Enough theory before each task | **Confirmed** — the check is a word-overlap test | Calculation answers are not judged at all |
| 5 | Less text on slides, more in notes | **Confirmed — the rules force the opposite** | Median 76 words on screen; notes pinned at the 50-word cap |
| 6 | Too many rules | **Confirmed** | ~108k tokens of rules per agent per module; 75 agents / 6.7M tokens for 3 modules |

---

## 1 · Photo shape and fit

**Cause — nothing reads the photo's pixel shape.**
- The layout is chosen by the script's `layout` field and word count only: `composition()`
  `course-factory/compile/scripts/compile_module.py:2206-2234` (a photo with more than 50 words goes to the
  "wide-left" column, `:2225`), then `auto_template()` `:2306-2328`.
- The picture-box sizing (`layout_fit.py`) is **skipped for photos**: `if fig and not is_photo` (`compile_module.py:3341`),
  so every photo gets the default box (`--lt-text: 55`, `course-module-ui/templates/gb_layouts.css:49`). Even if it
  ran, `layout_fit.aspect()` (`layout_fit.py:74`) reads only SVG/spec sizes, never a JPG/PNG.
- The script already records `picture.aspect` (e.g. "4:3"), but it is used only for placeholders (`compile_module.py:5158`).
- Photos are shown `object-fit: contain` (`gb_compose.css:619`), so a wrong shape becomes empty bands around a small photo.
- Correction to the first answer: the "never the same look twice" re-layout (L62) is **off** in real builds
  (`CF_LAYOUT_FLIP`, `compile_module.py:153-155`), so it is not the cause.

**Measured (243 photo placements):** 205 wide (≥1.2), 27 tall (≤0.85), 11 square. The photo column (slot ≈0.9-1.1)
holds 127 wide and 22 tall photos alike; wide photos use a median **66 %** of their box, 70 use ≤67 %. The framed-photo
layout (tall slot ≈0.75) held 4 of 4 wide photos.
Examples: PM M01 s06 (1.50 photo in a 0.71 slot, 44-47 % used) · IT M01 s03 (2.40 panorama in a side column, ~41 %) ·
IT M03 s04 (0.75 tall photo in a 1.24 slot, ~60 %). A builder already flagged it by hand: IGF `M17.build.json` s08.

**Fix**
1. Read the photo's size with Pillow (already imported in the compiler) in `composition()` / `auto_template()`:
   wide ≥1.3 → picture on top or across the slide (`figure-stage` / picture-top) or the column with the smaller text share;
   tall ≤0.85 → the side column; never a photo ≥1.2 in the framed (tall) slot.
2. Let the `layout_fit` boxes apply to photos too, with `aspect()` reading raster sizes.
3. Only after shapes match: `cover` + the existing `object-position` in the photo column.
4. Check: fit audit fails when a photo fills less than ~80 % of its box; unit tests with a 1600×900 and a 900×1600 photo.

## 2 · Slides cut into pieces

**Measured:** in all four courses, 0 teaching slides under 25 words (built decks: 578 slides, median 113 words) and
0 neighbouring same-Sub-ILO pairs that fit one slide by words. So "2-3 words a slide" did not appear in these builds.
What does appear:
- **Forced parts:** `parts_of` uses `k = max(2, …)` (`course-factory/scripts/content_script.py:1727`) — a slide in parts
  always has at least 2, even when it fits. IGF M17 s08: 83 words cut 23 + 60. IGF M18 s02: 107 words in 4 parts
  (26/44/22/15). A bare `"parts"` field switches it on (`compile_module.py:2380`).
- **"b" slides:** PM has 15 (e.g. M01 s09 36 words + s09b 66 words, same Sub-ILO). The writer is pushed to split by
  `t_template_mix` ("write it as its own slide", `page-labels.json:369`), "one idea per screen" (`course-type.json:8`)
  and `t_overfull` "move a part to the slide before" (`theory-rules.json:34`).
- **Nothing merges:** "keep every theory slide" (`script/GUIDE.md:162-164`); `t_thin_slide` is per slide only.

Ask Raivis which course/slide he saw — it may be a picture-only or task slide, or an older build.

**Fix**
1. `content_script.py:1727` → `max(1, …)`; ignore `"parts"` when the slide fits its budget.
2. New note `t_merge_neighbours`: consecutive plain slides on one Sub-ILO that fit one layout together.
3. Reword `t_template_mix` to "change it in place"; "one idea per screen, one screen per idea".

## 3 · Expert changes after the ILO review

**How it flows now:** a re-wording → `architecture.json` (`pedagogy_review.py:553-570`); a keep/Claude decision →
`pedagogy_review.json` "proposed" (`:573-581`); both only make the Stage 2 approval stale (`course_gate.py:114-125`).

**Gaps (code):**
- **Approved scripts and built modules never go stale.** `content_hash` covers the screens only
  (`content_script.py:244`); nothing records which Sub-ILO wording / review the script was written against. `render`
  skips the gate when the script is already approved (`:3606`); the compiler checks it only on `--init-build`
  (`compile_module.py:5810`).
- **The expert's Bloom level never reaches the check:** `bloom_of` reads `architecture.json` only (`content_script.py:2418`).
- **The writer's read list leaves out `pedagogy_review.json`** (`script/GUIDE.md:19-46`, "only these").
- **"done" is any non-empty text** (`pedagogy_review.py:165`) — never compared with a file change.
- **Dead path:** `bloom/GUIDE.md:168` forbids re-wording, so "take the proposed wording" (`course_portal.py:308`) can't fire.

**Real data:** no editor-mode answer exists in any course yet (PM: 16 rows from a relayed brief, IT: 0 answered). PM
scripts were approved after that brief. But PM topics 1.2, 2.2, 2.4 are Bloom 6 (Create) while M01's highest question
is level 4 and M02's level 3 — no check compares them.

**Fix**
1. On approve, store `based_on` = the module's Sub-ILO fingerprint + a hash of its review rows; `status`, `render` and
   `build_module` fail when it changed, naming the rows.
2. `bloom_of` takes the expert's level; add `pedagogy_review.json` to the writer's read list.
3. `done` must name a file changed after the note's date.
4. Test on a copy of one course: change a Sub-ILO in editor mode, confirm the script and build stop.

## 4 · Theory before the task — compact, not cut

**What the check really does** (`taught_share`, `content_script.py:934-965`, used at `:1149-1158`): takes the correct
answer's terms (numbers, 4+-letter words cut to 5 letters), ignores the question, and compares them with **every slide
since the module began**. For Bloom 3+, numbers not on a slide are dropped, so a calculation answer usually returns
"not judged" — a pass.

**Measured (PM M03, real functions):** q04 CPI passes only because "0.80" happens to be the SPI on s09; q06 SPI and
q16 cash balance (−3,000) not judged — and **q16 is a real miss**: s15 states the rule but never works the sum.
PM M02/M03: 5 questions not judged; IT M04: 8 of 21 judged on ≤2 words.

**Compact vs cut:** the guide contradicts itself — "never shorten" (`script/GUIDE.md:164`) vs "the writer shortens
them" (`:272-274`). The only survival test is new/old words ≥ 0.6 (`content_script.py:1867`) — facts are not checked.

**Fix**
1. For calculate / set-value / Bloom 3+ tasks: require an earlier slide on the same Sub-ILO with a worked example
   (or reveal) of that kind; compare the question's own terms too.
2. A "cold trainee" check (cheap agent): reads only the slides before a task and tries to answer; fails what it can't.
3. Compact-not-cut: replace the 0.6 word ratio with "every number and key term of the old slide still appears";
   fix the guide's contradiction.

## 5 · Less text on slides, more in the notes

**The rules force words onto the slide:**
- Notes 10-50 words, **must-fix** (`course-factory/knowledge/theory-rules.json:11-12`, "the theory belongs on the slide").
- Density 25 words per theory minute over slides + notes, **must-fix** (`:16`): with notes capped at 50, a 4-minute slide
  needs ≥50 words on screen, a 5-minute slide ≥75.
- "Answer taught first" ignores the notes (`content_script.py:1155`) — every tested fact must be on screen.
- Contradictions: `floor.json:29` "words moved to the notes" vs `layout-templates.json:26` "never cuts or moves words"
  vs `theory-rules.json:68` "no suggestion ever says … shorten its text".
- Font: body `clamp(15px, 2.5vmin, 30px)` ≈ 19-20 px on the tablet (`gb_layouts.css:53`); floor 12.5 px (`floor.json:5`).

**What the instructor sees:** the slide's `data-cue` on the trainer panel; `INSTRUCTOR_NOTES.md` is review-only
(the importer skips `.md`).

**Measured (PM M01-M03, 83 slides):** median 76 words on screen (max 150), 61 slides over 60 words; notes median 47 —
48 slides sit at the cap. Aigars's review: 10 of 18 notes asked for shorter text / bullets.
The factory already has the right shape — **"points"**: short points on screen, the full words to `data-cue`
(`compile_module.py:2884`) — but it is allowed only beside a picture and was used on 1 of 83 slides.

**Fix (needs Raivis's numbers — reverses the 2026-09-30 decision):**
- Notes 20-150 words (note, not fail), structured Say / Ask / Show.
- On-screen target ≤40-50 words (note); drop the 150 max and 30 min.
- "Answer taught first" counts the notes when the slide shows the point.
- "Points" becomes the default plain-slide shape, picture not required.
- Raise the body font floor to ~22 px.
- One rule text, one place: remove the contradicting lines.

## 6 · Too many rules

**What one agent reads to write and build one module:** script stage ≈232 KB (≈58k tokens: SKILL.md 36k,
script/GUIDE 41k, media-and-tasks.json 50k, blueprints 19k, layout-templates 18k, …) + compile stage ≈200 KB (≈50k:
compile/GUIDE 89k, vocabulary 29k, three other skills 63k, …). Law look-ups add laws-in-full 75k and owner-decisions 45k.
The PM build: **75 agents, 1,285 tool calls, 6.73M tokens, 3 modules, all 3 failed QA** (2026-11-05, factory ~2.10x).

- Of 496k characters of knowledge JSON, 19 % is `_why`/history keys (theory-rules 81 %, layout-templates 47 %).
- Checks: 106 FAIL, 45 NOTE, 22 WARN markers across 25 check scripts; content_script alone ~36-39 FAIL codes.
- Stale duplicates: the guide still says 50-150 slide words and 30+ note words (`script/GUIDE.md:191, 215-216`,
  `MANIFEST.md:1039`); the 85-word limit is stated in 5 places; `layout-templates.json:25` says both 110 and 70;
  the 150 max never applies because 85 comes first.

**Fix**
1. **Must-fix, read by the AI (short):** programme / ILOs / hours / sourced facts (L1-L4), no spill or scroll, font
   floor, a module check exists, tested answers visible to the trainee.
2. **Script-only** (the AI sees only the finding, never the rule): layout budgets, variety, parts, beside-picture
   limits, recap/self-check mix, 3D/photo word lists. Replace six knowledge JSONs (~121 KB) with a generated ~3 KB
   writer card. ≈28k tokens saved.
3. **History out:** every `_why` / dated key and version-tag prose to a history file never loaded. ≈5k per stage.
4. **Compile builders read `BUILDER_CARD` (12k), not `compile/GUIDE.md` (89k).** ≈19k saved.
5. **Drop duplicates**; style checks become notes.
Estimate: ~50k of ~108k tokens saved per agent per module (estimate, to be measured on a timed module build).

---

## 7 · Task variety and group tasks (Aigars: "it must vary much more, not the same drag-and-drop tasks; engaging tasks; maybe group tasks instead of self-checks")

**Measured (all self-check, module-check and final questions in the four courses, 805 questions):** the mechanic
*names* vary (12-14 kinds a course, never more than 2-3 the same in a row), but by **how the trainee answers** they
are almost all the same two things:

| Course | Tap an option | Drag cards | Type / set a number | Tap the picture | Operate (panel, 3D, sim) |
|---|---|---|---|---|---|
| Project Management (74) | 52 % | 32 % | 14 % | 0 | 0 |
| Information Technology (98) | 43 % | 27 % | 5 % | 23 % | 0 |
| Drošības pamatkurss (248) | 43 % | 43 % | 4 % | 7 % | 2 questions |
| IGF Advanced (385) | 41 % | 42 % | 9 % | 5 % | 4 questions |

**Team tasks: 0 in all four courses**, though the factory has them (`classroom-system.json` "team", codes TT1…) and the
classroom app on main splits a class into teams (`admin/classroom/control/control.js` teams).

**Causes**
- The mix rule (`theory-rules.json` "self_check": of five, three rich and two basic; `content_script.py:1108-1115`)
  covers **self-checks only**; module checks and finals (most of the questions) have no variety rule.
- Its "rich" list is equipment-only (tap, operate, 3D). Any free-text `basic_why` ("project management has no
  equipment") turns the must-fix into a note: PM used it 6 times, IT 4. Yet the families that make a management or
  IT task rich — investigate (spot the error in a real document, critique, find the fault), build (build the plan,
  fill the matrix), decide (scenario with consequences) — don't count as rich.
- Variety is counted by mechanic name, not by family: match → categorise → order is three different names and three
  times the same drag-the-cards.
- Nothing plans a team task: not the Stage 2 architecture, not the writer's guide, not a check.

**Fix**
1. Count variety by family (`media-and-tasks.json` "family": choose, decide, arrange, locate, operate, investigate,
   build) in **every** set: no two neighbouring questions of one family; no family over ~40 % of a set; a set of 4+
   uses at least 3 families. Must-fix for self-checks, note for module checks and finals.
2. Rich = locate, operate, investigate and build families (+ 3D / animation). `basic_why` no longer waives the rule.
3. One team task a module where a Sub-ILO is Bloom 3+ (a team case, plan or drill with roles leader / recorder /
   checker), planned at Stage 2 and replacing one self-check's Part B; a note when a module of 90+ minutes has none.
4. Engaging: Part B questions use the module's running case (the group's ship / project), with consequences.

**Clear what to do (Raivis's addition).** The task page says what to do only for 9 kinds (`task_pages.py` `*_say`:
order, sort, match, cloze, plan, matrix, errors, fault, panel — the drag lines added in 2.138.0 after IT M02 q04).
There's no line for single/multi choice (how many to pick?), true/false, tap the picture, label the drawing,
calculate (unit, rounding?), set a value, read the instrument, scenario, choose and justify, critique.
5. A what-to-do line for every kind; a multi-select says how many; a calculation gives its unit and rounding (check
   in the script: a must-fix when missing).
6. The task-readiness reviewer also flags unclear tasks: action not said, two asks in one, an unstressed "NOT",
   an option that gives the answer away.

## Recommended order

| Step | What | Needs | Model |
|---|---|---|---|
| 1 | Photo shape (§1) | nothing | Sonnet |
| 2 | Forced parts + merge note (§2 fixes 1-2) | nothing | Sonnet |
| 3 | Text and notes limits + "points" default (§5) | **Raivis's numbers** | Opus for the rule change |
| 4 | Expert changes reach the work (§3) | nothing | Opus |
| 5 | Theory before the task (§4) | nothing | Opus |
| 6 | Rule diet (§6) | Raivis signs the keep / script-only / drop list | Opus audit, Sonnet edits |

## Questions for Raivis
1. §5: the notes length, the on-screen word target and the font floor — are 20-150, ≤45 and 22 px right?
2. §2: which course and slide showed "2-3 words a slide"? Not found in the four local courses.
3. §6: may style checks (layout mix, variety, recap counts) become notes instead of must-fix?
