# Phase 5 — gap report: the owner's production process against today's factory

**Written 2026-09-30 · factory `course-factory` 2.10.0 + `nano-banana` 1.1.2 · analysis only, nothing changed yet.**

This compares Raivis's decision record (the "Phase 5" prompt) with what the factory actually says
and does today. Nothing in the skills has been edited. The next step waits for the owner's "go".

**Starting state, checked before writing this:** all six test files pass (139 tests, 0 failures),
and the official plugin check (`claude plugin validate --strict`) passes for both plugins and the
marketplace. So everything below is about *what the rules say*, not about broken code.

All file paths below are inside the factory folder
`C:\Users\raiviss\Desktop\factory-work\factory-mjaso` (skill files are under `plugin\skills\`);
any of them opens in Notepad or VS Code.

How to read the status words:

| Word | Means |
|---|---|
| **EXISTS** | the rule is already there and already says what the owner wants |
| **PARTLY** | something close is there, but it misses part of the owner's rule |
| **MISSING** | nothing in the factory covers it |
| **CONFLICTS** | the factory currently says something that goes against the owner's rule |

---

## 1 · Rule by rule

### Section 2 of the prompt — the fixed rules

| # | Owner's rule | Status | Where it lives today, and what is wrong |
|---|---|---|---|
| 2.1 | Style = the brand system only; never refuse a colleague's content or structure request | **CONFLICTS** | Nothing says "the operator's request wins". Several rules can be read as grounds to refuse or water down a request: `docs/FACTORY_LAWS.md:98-104` (L18 — content "locked, needing explicit authorisation", without saying the operator's own request *is* that authorisation) · `course-factory/SKILL.md:276-278` (expert-edited regions: "name the law and propose the fix … do not apply it") · `course-module-ux/SKILL.md:83-88` ("Compact or it does not ship") and `:90-94` ("do not write out what the instructor should say") · `FACTORY_LAWS.md:50-52` (L8 "explain and relocate; do not delete" — a colleague who says "delete this slide" gets a relocation) · `course-task-ux/SKILL.md:21-22` (the owner quotes are "not negotiable on style grounds"). The brand side is already right: `course-module-ui/SKILL.md:21-45` locks the look only, and says outright it does not decide content. |
| 2.2 | Programme and Main ILOs never change; a few Sub-ILOs may be added or re-expressed | **PARTLY** | L1–L3 exist (`FACTORY_LAWS.md:21-30`, `course-factory/SKILL.md:153-179`). Re-expressing Sub-ILOs is allowed; **adding** a Sub-ILO is not mentioned anywhere. |
| 2.3 | All IMO model-course equipment is assumed available | **CONFLICTS** | The factory asks about and doubts equipment: `templates/COURSE_BRIEF.md` "What is different" (simulator? facility? "anything the school does not have — say so"), the gate row "whether a practical needs a facility" (`course-factory/SKILL.md:360`), and it routes equipment questions to the org skill `novikontas-equipment-library` ("checking what Novikontas already has"). |
| 2.4 | More practice than theory; theory as active learning (self-check, "explain in your own words", predict-then-reveal, worked example then own attempt) | **PARTLY** | The 80 % active target and "theory delivered as active learning" exist and are enforced (L5, `course-factory/SKILL.md:181-211`, `hours/scripts/check_balance.py`). **Missing:** the named techniques. Nothing lists self-explanation, predict-then-reveal or worked-example-then-attempt as screen or task types. **Small conflict:** `course-task-ux/SKILL.md:115-132` forbids typing everywhere except simulator reporting, and "explain in your own words" invites typing. |
| 2.5 | Course type NEW_ENTRANT / EXPERIENCED declared at intake and changes how the course is made | **MISSING** | Only a sentence in a document that no skill loads: `docs/COURSE_PRODUCTION_PROCESS.md:110-113` ("A Basic course needs foundations … an Advanced course needs complex scenarios"). `course-module-ux/build/knowledge/audience-split.json` is instructor-vs-trainee, a different thing. |
| 2.6 | Three test levels: self-check (ungraded) · module check (**ungraded**) · final assessment (the only graded one). One task per screen, big targets, Next → Next | **CONFLICTS** | Module check is treated as scored: `course-task-ux/SKILL.md:5` ("a scored module check"), `:293-297` ("a self-check and a recorded check"), `:475-506` (pass mark `ceil(0.75 × questions)`, "PASSED / NOT PASSED" score sheets); `course-module-ux/build/knowledge/audience-split.json` ("the pass threshold" goes on screen); `docs/COURSE_PRODUCTION_PROCESS.md:184, 207` ("scored multiple choice", "the module check and its pass evidence"). The final assessment as a separate test already **EXISTS** (`build-order.json` step 13, `COURSE_PRODUCTION_PROCESS.md:201-202`). "One task per screen" is **PARTLY** there (`course-task-ux/SKILL.md:181` — "Part 2 is not on screen while Part 1 is unfinished"). The tablet app side is in §2 below. |
| 2.7 | Slides informative and visual — many real photos, animations, worked examples | **PARTLY** | L23 and `course-visuals` cover photos and teaching animation well. Worked examples are not named anywhere as a thing a slide should carry. |
| 2.8 | Visual order: knowledge base → old course → source files → internet → authored → generated. Keep legit old schematics | **CONFLICTS (order)** | `course-visuals/source/knowledge/asset-pipeline.json` levels 1–4: the knowledge base comes **last** inside level 1 and only "where a figure is genuinely needed"; there is no "old course" level (only "the course's own existing assets", which only exists in a retrofit); level 2 is a factory library the owner's list does not mention. L18 / retrofit (`course-factory/SKILL.md:244-246`) says an old visual's *decision* survives but "its small SVG does not have to" — which pushes toward redrawing legit old schematics instead of keeping them. |
| 2.9 | Modern animation: video clips (Veo), 3D (three.js bundled), richer canvas/WebGL, infographics — all local | **PARTLY / CONFLICTS** | Video generation exists (`nano-banana`, `realistic-visuals/SKILL.md:172-190`), and mp4/webm are allowed files. **Missing:** 3D/three.js, WebGL, generated infographics. **Conflicts:** `course-task-ux/SKILL.md:29-30` "no frameworks … no build step"; `course-visuals/SKILL.md:190` and `asset-pipeline.json` "Canvas only where SVG genuinely fails"; ES5 rule for shared engines (L6). **Technical trap:** new three.js releases are "module" files, and the publish check `gates.py` already fails module files because they do not work when a colleague opens the course by double-click. Only an older single-file three.js build works here. |
| 2.10 | Never stop at "I can't make this picture" | **EXISTS, with a wrong route** | L23 (`FACTORY_LAWS.md:186-191`) and `write_visual_handoff.py` already say "a module never stops because one picture is missing". **But** four files say the picture work is handed to `Agent(model: "fable")` as "a model that can generate": `FACTORY_LAWS.md:189`, `course-visuals/SKILL.md:79-80`, `orchestration/GUIDE.md:120-128`, `plugin/agents/visual-sourcer.md:132-133`. Fable is a text model and draws nothing. The real generator since 2.10.0 is the `nano-banana` plugin and its `image-director` agent. The instruction is out of date and sends the model down a dead end. |
| 2.11 | No "needs SME" spam; ask real expert questions batched as a pop-up with options, then continue | **PARTLY** | Markers stay off slides already (L22, `FACTORY_LAWS.md:166-168`). But every re-expressed Sub-ILO and every pass mark is marked `PROVISIONAL` "until the owner ratifies" (`course-factory/SKILL.md:173-175, 419`), and `course-task-ux/SKILL.md:447-450` tells the model to stop and write `[VERIFY: …]` when a UX fix seems to need a content change. The pop-up question tool is mentioned nowhere. |
| 2.12 | Learn from the operator: `FEEDBACK_LOG.md`, then an optional pattern file for future courses | **MISSING** | Closest is `templates/factory-notes.md` §9, which is feedback *about the factory*, written by the model, not the operator's corrections. Note: `plugin/resources/patterns/` already exists and holds **visual engines** (photo pins, stepped process, schematic) — the name is taken. |
| 2.13 | `COURSE_STATE.md` updated at the end of every stage | **MISSING** | Closest: `_factory/build.json` (a fingerprint record for expert-edit detection) and `factory-notes.md` (written once, at the end). Neither says "where are we, what is decided, what is next". |

### Section 3 of the prompt — the six stages

| Stage | Status | What exists, and the gap |
|---|---|---|
| **1 · Intake** | **CONFLICTS** | `course-factory/SKILL.md:128-140` allows **only three questions** (programme, knowledge base, "has anyone edited this by hand?") and "never web-search during intake". No question for old course or course type. The knowledge base is assumed to be **docling** in five places: `course-factory/SKILL.md:91, 133`, `knowledge/build-order.json:25` (step 3 "the project's docling extraction"), `templates/COURSE_BRIEF.md` ("the docling-extracted folder"), `docs/COURSE_PRODUCTION_PROCESS.md:51` (`kb_builder.py`, `00_INDEX/`), `orchestration/workflows/build_course.js:7`. The Course Source Processor format (checked on a real one at `Desktop\x\KNOWLEDGE_BASE`, tool 2.2.1: `COURSE_INDEX.md`, `SOURCE_MANIFEST.json`, `NEEDS_ATTENTION.md`, `sources/<name>/document.md + metadata.json + tables/ + images/`, `search_index/chunks.jsonl`, `retrieval/`) is not known to the factory at all. COURSE_LANGUAGE **EXISTS** (L19). "Look in the folder before asking" **EXISTS** (`SKILL.md:123-126`). |
| **2 · Course architecture → STOP** | **PARTLY** | The gate **EXISTS** (`SKILL.md:351-364`, `build-order.json` step 6) with programme, split, minutes, ratio, markers. The machine files exist (`programme.json`, `plan.json`, `MODULE_MAP.md`, `ILO_MAP.md`). **Missing:** a readable document a non-IT person double-clicks (today it is a table in the chat), the test plan (self-checks / module checks / final), where active learning replaces theory per module, practical tasks with equipment. |
| **3 · Module content script, word for word → STOP per module** | **MISSING** | Nothing like it. The nearest things are summaries, not the text: the screen inventory (`course-module-ux/SKILL.md:130-142` — "what is on it", one line per screen), the visual storyboard, and the task table (`course-task-ux/SKILL.md:73-83`). Today the operator sees the real slide text for the first time **after** the HTML is built. `build-order.json` goes GATE (6) → screen inventory (7) → visual system (8) → HTML. |
| **4 · Pilot Module 1, five roles → STOP** | **CONFLICTS** | `orchestration/GUIDE.md:1-9, 23` and `workflows/build_course.js:166-171` build **all modules at once** straight after the gate. There is one "module" agent that does everything (deck, tests, visuals); only QA and visuals are separate. Roles today: `visual-sourcer` agent (**EXISTS**, maps to role 3), `nano-banana:image-director` (**EXISTS**, pictures and video only — role 4 without 3D), a QA agent inside the workflow (**EXISTS**, but it checks against the maps, not against an approved script). No separate deck builder or test builder. |
| **5 · Remaining modules** | **PARTLY** | The parallel build and "QA behind each module" exist. Missing: each module's own script STOP and review STOP. |
| **6 · Final assessment, full QA, handover** | **EXISTS, mostly** | Final assessment (`build-order.json` step 13), cross-module check (`build_course.js:175-192`), preview → approval → publish (L21, `course-tablet-publisher`). Missing: the pattern-file offer (2.12). |

### Section 4 of the prompt — the reviewer's list, confirmed

All eight are real. Line numbers are in the tables above. One of them is worse than it looks:
the "module check is scored" assumption is not only in `course-task-ux` — it is built into the
tablet app's own web files too (next section).

---

## 2 · Every contradiction, and the fix I propose

### 2a · Between today's rules and the owner's prompt

| # | Contradiction | Proposed fix |
|---|---|---|
| C1 | **Module check scored** (`course-task-ux` description, §9, §15; `audience-split.json` "pass threshold"; `COURSE_PRODUCTION_PROCESS.md:184, 207`) vs 2.6 ungraded. | Rewrite those lines: module check = self-check at module level. It still reports "done" to the instructor, shows the reason for every answer, shows no PASSED / NOT PASSED and no pass mark. The final assessment is the only graded test and keeps every existing rule (programme's own count and pass mark, no answer key, re-sit = different paper). |
| C2 | **The tablet app itself scores module checks.** Checked read-only in `AndroidStudioProjects/NOVIKONTASTraining`: the Android program (`MainActivity.kt`) has no test logic and needs **no change**. But the app's shared web files do: `gb_tasks.js` describes checks as "PASSED or NOT PASSED" / "scored"; `gb_sync.js:380-403` sends `score / max / passed`; the instructor's live screen `live/live.js:377-386` paints each module chip **green or red** from `passed` — so a check that sends a score with no pass mark shows as a **red fail**, and one that sends no score shows nothing at all; `checks/m*/gb_score.js` are hand score sheets; `local_live/server/server.js:781` has the final pass mark fixed at 26 for GAS BASIC. The final assessment is already its own path (`final_assessment.html` → `GBSync.submitFinal()` → PDF to Google Drive). The database needs no change (`passed` may be empty). | The factory cannot change the app (L21). I will (a) make new courses send a module check as `kind: "check"`, `state: "submitted"`, `passed: null`; and (b) write a short, exact change list for the app's web files (live-screen chip shows "done" instead of pass/fail; check wording; pass mark read from the course instead of fixed at 26) for the owner to apply in the app. **Owner decision Q1.** |
| C3 | **Three intake questions only** (`SKILL.md:128-140`) vs Stage 1 (old course, course type, expert questions). | Keep "look in the folder first" and "batch, never one at a time". Replace the fixed list of three with: programme (blocking) · knowledge base · old course · course type · IMO model course · language (only if it cannot be read off the material) · expert-edits question (unchanged, only when the detector cannot tell). All in one pop-up batch. |
| C4 | **Equipment is questioned** (brief, gate, org skill) vs 2.3. | Default: everything in the IMO model course's equipment list is available. Ask only if the operator says otherwise. Remove "anything the school does not have" from the brief. |
| C5 | **All modules at once** (`orchestration/GUIDE.md`, `build_course.js`) vs Stage 4 pilot. | The shape becomes: reader → architecture STOP → script M1 STOP → build M1 → review STOP → then the rest in parallel, each with its own script STOP. `build_course.js` gets a `pilot` pass. |
| C6 | **Build order has no content-script stage** (`build-order.json` 6 → 7). | Insert "content script" between the gate and the screen inventory. The screen inventory is then *derived from* the approved script instead of being a separate approval. |
| C7 | **Docling only** (five places, listed in §1 Stage 1). | Add a small "knowledge base" lane that recognises both kinds by their files, and a search script that reads the Course Source Processor's own index (`search_index/chunks.jsonl`) and writes a retrieval pack the same way the SEARCH tool does — so a session never has to open the SEARCH window or read a whole book. |
| C8 | **No instruction "the operator's request wins"** — L18, L8, L24, compact budgets, "not negotiable on style grounds". | One short rule in `course-factory/SKILL.md` and a new law: the only hard limits are brand, Main ILOs + programme, hours, no-source-no-claim, tablet offline. Everything else the operator asks for is done. If it truly hits a hard limit: one or two plain sentences why, the closest option that works, then do it. Add one line to L18: *an operator's request in chat is the explicit authorisation*. |
| C9 | **Visual order** (`asset-pipeline.json`) vs 2.8. | Reorder the levels to KB → old course → source files → (factory library, kept as a quiet step before the internet) → internet → authored → generated. Add: a legit schematic or photo from the KB or old course that teaches well is **used as it is** (only framed in the new style), not redrawn. **Owner decision Q2 (picture rights).** |
| C10 | **"No frameworks" / "Canvas only where SVG fails" / ES5** vs 2.9. | Keep ES5 for the factory's own shared engines. Allow a pinned, locally bundled library for a teaching figure (three.js in its older single-file form, MIT licence, stored once inside the plugin), canvas/WebGL when the figure needs it, and short local video. Every one still has to teach a mechanism (L13) and pass the "does it move / respond" check (L20). |
| C11 | **Typing forbidden** (`course-task-ux §2`) vs "explain in your own words" (2.4). | No typing: "explain-then-reveal" — the trainee thinks or says the answer, taps **Show**, compares with the model explanation, and taps "I had it / I missed something". Ungraded, no keyboard, nothing to mark. If the owner wants free typing in these, say so. |
| C12 | **PROVISIONAL / [VERIFY] everywhere** vs 2.11. | Keep the markers, but only inside `factory-notes.md`, never as a reason to stop. Sub-ILO changes are shown once at the Stage 2 STOP; the operator's "next" ratifies them. Real expert questions: collected and asked at the next STOP as one pop-up batch. |
| C13 | **Word budget "compact or it does not ship"** vs NEW_ENTRANT "more explanation". | Not a real clash if handled one way: NEW_ENTRANT gets **more screens and more worked examples**, not denser screens. Each screen stays readable; the extra explanation goes onto extra screens. |
| C14 | **"Do not narrate what the instructor says"** (`course-module-ux` law 4) vs Stage 3 "instructor notes". | Instructor notes in the script are the instructor's key points and cues (`data-cue`), not a speech. Compatible once written down. |

### 2b · Contradictions inside the factory itself (found while reading)

| # | Where | What is wrong | Fix |
|---|---|---|---|
| I1 | `_claude/CONTEXT.md:5, 25`, `00_READ_ME_FIRST.md:3, 54` | Both say "Phase 3 complete, plugin 2.1.0", "sixteen laws", and point to `plugin/CLAUDE.md`, which was deleted. The factory is 2.10.0 with 25 laws. **`CONTEXT.md` is the file every new session is told to read first**, so every session starts with a 2.1.0 picture of the factory. | Rewrite both to the current state. |
| I2 | Three numbering systems for the laws | `course-factory/SKILL.md` numbers its own "nine laws" 1–8 + 5b; `FACTORY_LAWS.md` numbers L1–L25; the orchestration files use a third mix: `build_course.js:83` and `orchestration/GUIDE.md:46` call COURSE_LANGUAGE "L6" (it is L19; L6 is tablet-first), `GUIDE.md:47` calls the visual system "L12" (L12 is picture rights). `FACTORY_LAWS.md:196` (L24) says "L5 says the existing delivery…" — that is L18. | One numbering: the L-numbers everywhere. |
| I3 | `knowledge/build-order.json:148-158` | The "non-negotiable orderings" still use the old step numbers: "task pages (9)" is step 10, "screens (10)" is 11, "verify (15)" is 16. `course-module-ui/SKILL.md:18` also says "verify (step 15)". The file that is "the authority on order" contradicts itself. | Renumber (the new stage will renumber them again anyway). |
| I4 | Four files, see 2.10 above | Picture generation routed to `Agent(model: "fable")`. | Route to `nano-banana:image-director`, with the manual Gemini-app route as the fallback (already written in `realistic-visuals`). |
| I5 | Headers of `course-factory`, `course-module-ux`, `course-task-ux`, `course-tablet-publisher` SKILL.md | "Personal — installed for Raivis only, not org-published" — but they ship to colleagues through the marketplace. `course-visuals` says "plugin 2.1.0". | Correct the headers. |
| I6 | `COURSE_PRODUCTION_PROCESS.md:241` | "seven checks" — the verify list in `SKILL.md:427-482` has fourteen. | Rewrite this document to the six stages; it becomes the operator-facing description. |

### 2c · More contradictions inside the factory (from a search of every file, each one re-checked)

| # | What disagrees | Fix |
|---|---|---|
| I7 | **Where the module check sits.** "ALWAYS the last screen" in `course-module-ux/build/GUIDE.md:54, 137` and `build/knowledge/screen-kinds.json:137`; but "second-to-last, hand-off screen last" in `measure/knowledge/floor.json:50-53` and `tablet/scripts/verify_course.py:10`. The measurement file records that the owner changed this on 2026-09-03, so the build guide is the stale one. | Build guide and screen kinds say "second-to-last, hand-off last". |
| I8 | **The gate asks for a screen count it cannot know yet** — `course-factory/SKILL.md:360` wants "screen count" per module at the gate, but screens are only listed at step 7, after it. | In the new process the screen count comes out of the Stage 3 script, so it leaves the Stage 2 STOP. |
| I9 | **How many questions may be asked** — "only these three" (`SKILL.md:128`) vs "two to four at a time" (`COURSE_PRODUCTION_PROCESS.md:54`). And `UNKNOWN` means "asked, the operator did not know" (`SKILL.md:417`) but also "not in the brief means UNKNOWN", with nobody asked (`SKILL.md:140`). | Replaced by C3; `UNKNOWN` keeps one meaning: asked and not known. |
| I10 | **Approvals disappear in the parallel build.** The screen inventory and the visual storyboard each need approval (`course-module-ux/SKILL.md:136`, `course-visuals/decide/GUIDE.md:16`), but the parallel workflow builds straight through after one gate (`build_course.js:102-128`). | The pilot + per-module script STOP (C5, C6) put the approvals back where the owner wants them. |
| I11 | **Whether an agent may do the checking.** The workflow adds QA agents (`orchestration/GUIDE.md` rule 4); the blueprint says "no agent for verification" (`COURSE_FACTORY_BLUEPRINT.md:269`). And the orchestration guide calls a parallel build "not the hard part" while `GOLDEN_COURSE_EXTRACTION.md:150` calls parallel module agents the cause of the visual drift — "the single most important production lesson". | The owner's Stage 4 decides it: QA is an agent, and the main conversation still reads its findings. The pilot exists partly to catch drift before the fan-out. |
| I12 | **Commit and push.** "Never commit or push — that is the owner's" (`tablet/GUIDE.md:113`, `delivery-contract.json:88`, L16) vs the publisher, which commits, pushes and can merge after the owner's approval sentence (`course-tablet-publisher/SKILL.md:76-99`). | Not a real clash once written down: the publisher may commit *only* after the approval sentence (L21). Say so in `tablet/GUIDE.md`. |
| I13 | **Repainting shipped modules.** Retrofit moves a module onto the new look freely (L18), but `course-module-ui/SKILL.md:65-67, 182` and `build-order.json:138` say "never repaint a signed-off deck". Retrofit verify runs "every new-build check", including the strict look check that must never run on shipped modules. | Say plainly: a retrofit the operator asked for **is** the owner's go-ahead to repaint that module; the strict look check runs on the rebuilt files only. |
| I14 | **What "80 %" measures.** L5 in `FACTORY_LAWS.md:37` says "80/20 practical"; `course-factory/SKILL.md:199` says the 80 % is learner-active minutes, not the practical share. | Owner's 2.4 ("more practice than theory, theory as activity") matches the SKILL.md meaning; L5's title is corrected. |
| I15 | **Picture levels.** L23 skips the factory library level; `course-visuals/source/GUIDE.md:19-21` asks for a generation brief after levels 1–2, while `GENERATED_ASSET_BRIEF.md:3` requires levels 1–3. | Settled by the new order in C9. |
| I16 | **Where the hours table is read from.** "Never from the knowledge base" (`COURSE_PRODUCTION_PROCESS.md:65`) vs the brief template, whose example is the programme's knowledge-base copy (`templates/COURSE_BRIEF.md:15`). | The example points at the original programme file. |
| I17 | `FACTORY_LAWS.md:35` points to a fallback folder `resources/org-dependencies/` that does not exist (the real one is `course-factory/org/ORG_DEPENDENCIES.md`). | Correct the path. |
| I18 | **"Read it, do not restate it", then restated.** `course-factory/SKILL.md:155, 226` and `build-order.json` say the order must not be restated, and `SKILL.md:371-373` restates it — wrongly (the ILO map after the gate, no visual-plan step). The honesty-marker table is copied in nine files. | Replace the restated order with a pointer; the marker table stays in one place, others point to it. |

---

## 3 · Why the factory is likely working poorly — with evidence

**1 · The operator sees the real text only after everything is built.** The one approval before
building is a table of minutes and module split (`SKILL.md:351-364`). The words on the slides, the
test questions and the answers are first seen in finished HTML. Every content correction then
lands on built pages, which is the most expensive place to change anything, and the factory's own
"edit, don't regenerate" and "expert edits are protected" rules make those corrections slower
still. Stage 3 (the content script) fixes this at the root.

**2 · The rules are written as stories and absolutes, and many of them pull toward "no".**
There are 25 laws plus the per-skill laws, and most are written as "never", "not negotiable",
"do not", with a war story behind each. Nothing tells the model which ones can bend when the
operator asks. A model reading "compact or it does not ship", "explain and relocate; do not
delete", "content is locked" and "name the law … do not apply it" in the same breath will
reasonably conclude that pushing back is the safe choice. That matches the owner's complaint
that colleague requests get refused or ignored "because of the style".

**3 · New sessions start from a wrong picture.** The first file a new session is told to read
(`_claude/CONTEXT.md`) describes version 2.1.0 and a plan that has since been built (I1).
What to do: I will fix it in step 0 of the plan below; afterwards the file names 2.10.x and the
six stages.

**4 · The instructions point to things that do not work or do not exist.** "Fable generates the
picture" (I4), step numbers that no longer match (I3), law numbers that mean different things in
different files (I2), `plugin/CLAUDE.md` (deleted), docling-only knowledge bases (C7). Each one
costs the model a wrong turn, and some turns end with "I cannot make this picture".

**5 · Too much loads at once.** Measured by following every "read this" instruction one level
down (size ÷ 4 ≈ tokens):

| Build step | Loads | Running total in one session |
|---|---|---|
| programme → gate (steps 1–6) | `course-factory/SKILL.md` (30 KB), `build-order.json` (17 KB), hours, coverage, org fallback, brief | ≈ 19,000 |
| screen inventory (7) | `course-module-ux` router + build guide (18 KB) + two rule files | ≈ 30,500 |
| visual system (8) — **the heaviest** | `course-module-ui` + tokens + four style files (the composition file alone is 31 KB) | ≈ 51,000 |
| visual plan (9) | `course-visuals` + seven rule files | ≈ 70,000 |
| task pages (10) | `course-task-ux/SKILL.md` (28 KB) + two style files | ≈ 82,000 |
| screens (11) | slide rules, deck engine, generation brief, `realistic-visuals` | ≈ 91,000 |
| terminals (15) | publisher + platform file (18 KB) + three references | ≈ 109,000 |
| verify + notes (16–17) | measurement guides, traps, floors, four notes templates | **≈ 128,000** |

Plus about 2,100 tokens of skill descriptions in *every* conversation. In the parallel build,
each module agent reloads roughly 80,000 of this before it writes its first slide — eight modules
is about 640,000 tokens of rules before any content. So by the time a single session reaches the
slides, the actual course material competes with 90,000 tokens of rules, many of them repeated:
"changing a row is free" appears in 8 files, "a green exit is not proof" in 8, the honesty-marker
table in 9. Much of the visual-system step is reading whole style files the model only needs to
**copy**, not understand. This is the most likely reason for "weak" output: little room left for
the source material, and many "never" rules competing for attention.

Where the owner's new detail should go, to avoid making this worse: in lane files that load only
at their stage (intake, script, tests, motion), never in the always-read SKILL.md files. The new
content script also *reduces* the load of the build: the deck builder works from one approved
script instead of re-deriving content from the knowledge base.

**6 · The factory has never been run on a real second course end to end.** Its own documents say
so: `_claude/CONTEXT.md:132` ("Not proved: any of it against a real course") and
`COURSE_FACTORY_BLUEPRINT.md` §10 step 9 ("the acceptance test"). The rules were tested on
fixtures. The pilot stage in the new process is exactly that missing test.

---

## 4 · Implementation plan — small steps, each one tested

Every step: I prepare the change and the version number; the owner commits, pushes and installs
(L16). After every step I run all existing tests, the plugin check, and the step's own new test,
and report failures as plainly as passes (L15). Versions: one minor bump per step (`2.11.0`,
`2.12.0` …); `nano-banana` bumps only when its files change.

| Step | What | Files touched | Version | How it is tested | Risk |
|---|---|---|---|---|---|
| **0** | **Clean up the wrong pointers** — I1–I7 and I12–I18: current state in `CONTEXT.md` and `00_READ_ME_FIRST.md`; one law numbering; step numbers in `build-order.json`; picture route → `image-director`; stale headers; module check second-to-last; wrong paths and restated order. No rule changes. | `_claude/CONTEXT.md`, `00_READ_ME_FIRST.md`, `docs/FACTORY_LAWS.md`, `build-order.json`, `orchestration/GUIDE.md`, `build_course.js`, `course-visuals/SKILL.md`, `visual-sourcer.md`, `course-module-ux/build/GUIDE.md`, `screen-kinds.json`, `tablet/GUIDE.md`, `COURSE_BRIEF.md`, 5 SKILL.md headers | 2.10.1 | all tests + plugin check; a search that no file still says "fable" as a generator, "L6" for language, or `plugin/CLAUDE.md` | Low |
| **1** | **The owner's decision record as law** — new laws: L26 *the operator's request wins; style = brand only* (with the hard-limit list and the "explain in two sentences, offer the closest option, do it" rule); L27 three test levels; L28 course type; L29 content script before HTML; L30 pilot first; L31 state, feedback and patterns. One short "precedence" block in `course-factory/SKILL.md`; one line in L18. No NEEDS-SME rule (C12). | `FACTORY_LAWS.md`, `course-factory/SKILL.md`, `course-module-ux/SKILL.md` (law 3, 4, 7 one line each), `course-task-ux/SKILL.md:21-22` | 2.11.0 | all tests; add routing cases to `test_routing.py` ("add two more slides on X", "delete slide 5", "more examples") that must select course work, never a refusal | Medium — wording that changes behaviour |
| **2** | **Intake (Stage 1)** — new question batch as a pop-up; equipment default (C4); course type; old course (local folder, Drive link optional); knowledge-base lane for both formats + `kb_search.py` (reads `chunks.jsonl`, writes a retrieval pack, standard Python only). | `course-factory/SKILL.md` (brief section), `templates/COURSE_BRIEF.md`, new `kb/GUIDE.md`, `kb/knowledge/kb-formats.json`, `kb/scripts/kb_search.py`, `build-order.json` step 3, new `knowledge/course-type.json` | 2.12.0 | new `test_kb_search.py` on small fixtures of both formats; a read-only run on the real `Desktop\x\KNOWLEDGE_BASE` writing its pack to a scratch folder; `check_plain_language.py` on the new guide | Medium |
| **3** | **Memory: `COURSE_STATE.md`, `FEEDBACK_LOG.md`, pattern files** — two templates; the rule "update the state at the end of every stage"; log every operator correction; offer a pattern file at the end; future courses read patterns as guidance only. | new templates in `course-factory/templates/`, `SKILL.md` (a few lines), new folder `plugin/resources/course-patterns/` (the name `patterns/` is taken) | 2.13.0 | templates present and referenced; plain-language check; a dry "resume" test: a new session given only the course folder can say the stage and next step | Low |
| **4** | **Stage 2 review page** — the architecture as one page that opens with a double-click and prints to PDF: modules, Main ILO and Sub-ILOs per module, hours, ratio, where active learning replaces theory, practical tasks and equipment, the test plan. Built from `plan.json` + the ILO map by a script, in the brand style. | new `course-factory/scripts/make_architecture_page.py`, `SKILL.md` gate section, `build-order.json` step 6 | 2.14.0 | fixture → page renders in the browser, no network requests, plain-language check | Low |
| **5** | **Stage 3 content script** — new lane `script/GUIDE.md`; the editable twin `MODULE_SCRIPT.md` (per slide: exact text, planned visual, instructor cues; every self-check and module-check question with answer and feedback; final-assessment bank); a script that turns it into the review page / PDF; how corrections come back (chat, edited twin, PDF comments where readable); `check_script_match.py` so QA can prove the slides say exactly what was approved. The screen inventory is derived from the approved script. Word budget and slide-text checks run on the script, before any HTML. | new `course-factory/script/…`, `build-order.json` (new step), `course-module-ux/SKILL.md` gate section, `check_slide_text.py` (accept the script as input) | 2.15.0 | new `test_script_match.py` (a changed word must fail, a restyled slide with the same words must pass); render test; all old tests | **High** — the biggest new piece |
| **6** | **Three test levels** — C1, C11; one task per screen, Next → Next; the module-check reporting rule (`passed: null`); a new check in `check_task_pages.py` that a module-check page computes no pass/fail; the change list for the app (C2) as a separate plain document for the owner. | `course-task-ux/SKILL.md` + `MANIFEST.md`, `audience-split.json`, `screen-kinds.json` (check), `build-order.json` step 13, `check_task_pages.py`, new `docs/ANDROID_CHANGES_FOR_UNGRADED_CHECKS.md` | 2.16.0 | new fixtures for the task check (scored module check → finding; ungraded → clean; final assessment scored → clean) | Medium — the tablet's live screen shows red until the app changes |
| **7** | **Active learning + course type in the build** — named patterns (self-check, explain-then-reveal, predict-then-reveal, worked example → own attempt, faded example, scenario "what would you do") as screen / task kinds; what NEW_ENTRANT and EXPERIENCED each change (screens per topic, worked examples, scenarios, theory length). | new `course-module-ux/build/knowledge/active-learning.json`, `screen-kinds.json`, `course-type.json` (from step 2) | 2.17.0 | `check_balance.py` still accepts / rejects its fixtures; new kinds pass `check_static.py` | Medium |
| **8** | **Visual order and old course** — C9: reorder the levels; old course as its own level; "keep legit old schematics"; rights rule per Q2. | `asset-pipeline.json`, `resolve_asset.py`, `visual-first-rules.json`, `source/GUIDE.md`, `visual-sourcer.md`, L12/L23 text | 2.18.0 | new fixture test for `resolve_asset.py` (KB beats old course beats source files; nothing found → generation brief) | Medium — code change |
| **9** | **Modern motion** — C10: video, 3D, WebGL/canvas, infographics as representations; a pinned local three.js (older single-file build) in the plugin; tablet rules for video (short, small file, poster, starts on tap — the app requires a tap before video plays); `check_visuals.py` still fails any remote file. Extend `image-director` for infographics and 3D stills. | `course-visuals/decide/knowledge/representations.json`, `review/knowledge/motion-rules.json`, `check_visuals.py`, `verify_figures.js`, `plugin/resources/vendor/three/`, `nano-banana/agents/image-director.md` | 2.19.0 + nano-banana 1.2.0 | a sample 3D figure and a sample video screen open by double-click with no network, pass the publish check, and `GBVerifyFigures.motion()` reads them as alive. **Needs one test on a real tablet** — WebGL and video on the actual device cannot be proven from this computer | Medium–high |
| **10** | **Five-role pilot orchestration** — C5: new agents `deck-builder`, `test-builder`, `module-qa` (checks against the approved script); `image-director` extended as Motion & 3D; `visual-sourcer` unchanged. Order inside a module: tests + visuals + motion first, then the deck, then QA. Each agent writes only its own sub-folder. `build_course.js` gets the pilot pass; the same shape works with plain agents when the Workflow tool is not switched on. | `orchestration/GUIDE.md`, `build_course.js`, new files in `plugin/agents/` | 2.20.0 → I suggest **3.0.0**, since the whole pipeline changes | `claude plugin validate --strict`; the workflow's pass 1 on a fixture course stops at the architecture STOP | **High** — only a real pilot proves it |
| **11** | **Lighter loading** — move the long stories out of the always-read SKILL.md files into lane/reference files that load only when needed. Nothing deleted. Only if the owner agrees (**Q4**). | `course-factory/SKILL.md`, `course-task-ux/SKILL.md`, their MANIFESTs | 3.0.x | before/after size measurement; all tests; the routing tests still pass | Medium — these rules came from real failures, so moving must not lose one |
| **12** | **Documents** — rewrite `COURSE_PRODUCTION_PROCESS.md` to the six stages, update `CONTEXT.md`, every skill's maintainer file (MANIFEST), `INSTALL_FOR_COLLEAGUES.md` where it changed. | `docs/`, `_claude/`, MANIFESTs | with the last step | plain-language check on the operator-facing documents | Low |

**Then the real test:** one pilot module of a real course through Stages 1–4 (**Q5**). Every
earlier phase was proven on fixtures only; this is where the process is actually proven.

---

## 5 · What I need from the owner — decisions only

**Q1 · The tablet's instructor screen and ungraded module checks.**
Today the instructor's live screen colours each module check green or red, and a check with no
pass mark shows **red**. The factory may not touch the app. Choose:
(a) the factory writes an exact change list for the app's web files and you apply it *(recommended)*;
(b) you want the factory to prepare the changed files for your review in a separate folder;
(c) leave the app, and new courses send no score for module checks (the chip then shows nothing, not even "done").
Also: should an ungraded module check **still wait for the instructor to unlock it**, as today? *(I recommend yes — it keeps the class together.)*

**Q2 · Pictures from the knowledge base and the old course — whose rights?**
Your order puts the KB first. The KB holds whole textbooks (for example the Theraja and Callister
books in the electrical KB). Today a publisher figure is `RIGHTS_REVIEW_REQUIRED` and **blocks
shipping**. Choose:
(a) Novikontas's own material (old courses, own manuals, own photos) is treated as our own and used freely; textbook and publisher figures are **redrawn** as our own schematic, credited "after <book>", and never copied *(recommended)*;
(b) figures copied from the KB are accepted for internal training with a source credit — your decision as the owner;
(c) keep today's rule unchanged.

**Q3 · Safety equipment with no real photograph anywhere.**
Today the factory never generates a picture of safety-critical equipment a trainee must recognise;
it waits for a real photo. With "never stop" (2.10), choose:
(a) generate it, clearly labelled "AI-generated illustration" on the slide, and list it in the notes for you to replace later *(recommended)*;
(b) keep the rule: the slide ships without it and the handoff says what photo to take.

**Q4 · May I move (not delete) the long stories out of the two biggest skill files** into files
that load only when needed (step 11)? It makes every session lighter. Every rule stays, word for word.

**Q5 · Which course and module is the first real pilot?** (for example the electrical course whose
knowledge base is in `Desktop\x`).

Everything else in this report I will decide as proposed unless you say otherwise — in
particular: no typing in "explain in your own words" tasks (C11), NEW_ENTRANT gets more screens
rather than denser ones (C13), pattern files go into `plugin/resources/course-patterns/` so every
colleague receives them with the next update, and a minor version bump per step.

**Say "go" (with your answers) and I start with step 0.**

---

## 6 · The owner's answers — 2026-09-30 ("Go", plan approved with changes)

**Order.** Step 0 → **step 11 (lighter loading) straight after step 0**, before any new rule, so
new lanes land in the lighter structure; token counts before and after; every test still passes.
Then steps 1–5, then **STOP**: the owner gives the pilot course, and Stages 1–3 run on it
(intake, architecture page, Module 1 content script). The owner reviews the real content before
steps 6–10 (tests, visuals, motion, agents). After step 10, the pilot finishes by building
Module 1. After **every** step: stop, a short plain summary, the exact commit and push commands.

**Q1 — (a).** The factory writes the exact change list for the app's web files; the owner applies
it. The ungraded module check **still waits for the instructor's unlock**. The instructor screen
shows *done / not done* and the result as information only — never pass/fail, never red.

**Q2 — (a), plus:** a redrawn textbook figure must be **technically identical** to the original,
never simplified. Every "after <book>" figure is listed in `factory-notes.md` so the owner can
check licences with management; if Novikontas is licensed, the originals replace the redraws.
The ICS/SIGTTO "not cleared" rule stays.

**Q3 — not (a) for equipment the trainee must recognise** (markings, controls, valves, PPE): use
an accurate schematic and add the item to a **"photos to take at Novikontas"** list — the
equipment is there. AI illustrations, labelled "AI-generated illustration", only for general
context images.

**Q4 — yes.** Move, do not delete.

**Q5 —** the pilot course name and folder come after step 5.

**C11 — approved:** explain-then-reveal, no typing.

**Also:** knowledge-base search packs are written into the **course folder**, never into the
knowledge base (it is read-only). Every step confirms that nothing breaks the published GAS BASIC
course on the tablets.
