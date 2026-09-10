# Factory rule classification

Every rule, procedure and artefact found in the golden course and the existing skills, sorted into
the eight categories Phase 1 asked for. Duplicates are consolidated. Contradictions are named at the
end rather than silently resolved.

Categories:
**LAW** permanent rule · **SKILL** reusable procedure · **AGENT** isolated specialist work ·
**HOOK** deterministic protection · **COMPONENT** reusable implementation ·
**GOLDEN** reference example · **ANDROID** integration contract ·
**SPECIFIC** do not generalise · **DISCARD** obsolete

---

## 1 · GLOBAL FACTORY LAW — permanent, belongs in `CLAUDE.md`

Sixteen candidates. Each earned its place by costing real rework; the evidence column says where.

| # | Law | Evidence |
|---|---|---|
| **L1** | **The approved study programme is law, and minutes are the law's units.** An academic hour is whatever the programme says (GAS BASIC: 40 min) — never assume 60. Every module's built teaching time equals its allocated minutes **exactly**. Anything that will not fit becomes self-study in the handout; the handout is the overflow valve, class time is fixed. | Built to 2175 min against an accredited 1640 — a 33 % overrun found only after all eight modules existed |
| **L2** | **Main ILOs are copied verbatim and never edited, renumbered or improved.** Sub-ILOs may be re-expressed for teaching, are marked `PROVISIONAL` until ratified, and are **never renumbered anywhere a trainee can see**. A semantic change is proposed explicitly, never introduced quietly. | `ILO_SUBILO_PROPOSALS.md`; the 2026-08-27 SME round withdrew all three proposed splits |
| **L3** | **Official hours are never changed to fit delivery scheduling,** and the factory never fabricates attendance, delivered contact time or a compliance record. Operational scheduling is a separate, instructor/organisation responsibility. | `SHARED_PRODUCTION_RULES` §A; owner's 2026-09-07 four-day ruling recorded `delivery_days` beside the untouched accredited `days: 4` |
| **L4** | **NO SOURCE = NO MARITIME CLAIM.** Never fill a gap from model memory. A stated gap is a good answer; an invented fact is a failure however plausible. Authority tiers, never upgraded: 1 approved programme · 2 STCW and mandatory instruments · 3 IMO model course (1.04 is DRAFT) · 4 conventions and codes · 5 simulator/equipment manuals, **own equipment only** · 6 industry guidance · 7 legacy course material, design reference only. Check every source's **edition on its own cover page**. | `PROJECT_RULES.md`; two live traps in the corpus — a 1997 MARPOL and a 1995 ICS guide |
| **L5** | **80 / 20 practical, or theory delivered as active learning.** Where the programme's own table makes 80 % arithmetically impossible (GAS BASIC: 8 practical hours of 43 = 19 %), the theory hours are delivered as active learning — a task inside the theory block, not a longer lecture. **A theory block with no trainee activity in it is a defect.** Presentation is not the default method and is never mandatory. | `PROJECT_RULES.md`; `SHARED_PRODUCTION_RULES` §B; architecture result ≈83 % active |
| **L6** | **Tablet-first, touch-first, offline.** A finger on an 800×1280 portrait screen first, then landscape, then the projector. Targets ≥ 44 px, no hover-only affordance, minimal typing, ES5 in shared engines, nothing at class time depends on a network. | `course-module-ux` law 6; the Android contract |
| **L7** | **Nothing is useless until you have grepped for what depends on it.** Grep the id, class, label and filename across both terminals, the course tree and every generated script before removing anything. | Three of four "useless" findings were load-bearing: timer buttons the run script tells the instructor to press, print buttons on handouts, and hrefless `<span id="gb-home">` |
| **L8** | **Explain and relocate; do not delete.** "Why is this here?" is a report about the presentation, not proof the thing is useless. Find its job, keep it, say its job in plain words, move it to where that job happens. **Cutting usable material to satisfy a complaint is a worse defect than the clutter was**, because the clutter was visible and the loss is not. | Owner, verbatim; `course-module-ux` law 7 |
| **L9** | **Edit; do not regenerate.** Freeze stable approved artefacts and patch them with scripts. Regenerating burns quality, consistency and budget. | Owner, verbatim; `PROJECT_RULES.md` production rule |
| **L10** | **Visible must be sufficient, not merely short — and if a visible line refers to something, name that something on the same line.** This outranks any word budget. A 60-word screen that cannot be acted on without opening a `<details>` is worse than the 300-word screen it replaced. | Owner, repeatedly: *"what is console? what is that??????"* |
| **L11** | **A generated file is never hand-edited,** carries `DO NOT HAND-EDIT` in its header, and is regenerated after any change to its input. Overrides live inside the generator and a rotted override stops the run. | Hand-written slide references broke 96 cross-references in Modules 5 and 6; the instructor announced the wrong task in the room |
| **L12** | **Every asset carries provenance, a licence and a visual verification, in a metadata file beside the file.** Photographs: CC0 / CC BY / CC BY-SA / public domain only. Open and look at every file before use. Never a misleading AI pseudo-photograph of safety-critical equipment. Never contradict named kit. Caption a near-miss honestly. | A file named "Arctic Princess LNG carrier" was a small red cargo ship; six ICS/SIGTTO figures currently block issue |
| **L13** | **A visualisation must explain a mechanism, state change, relationship, flow, sequence or cause/effect.** Decorative movement is not sufficient. Cards, icons, arrows and CSS transitions are not instructional visualisation. Explain first, then show — split text and animation when they compete. A value interpolated inside a sourced chart is marked as such. | Module 1's five named engines, each with a cited source and `~` on interpolated points |
| **L14** | **The reference course, `source_files/`, the knowledge base and the Android application are read-only to the factory.** The factory writes into a course project and, on explicit instruction, into a course pack. | `PROJECT_RULES.md`; the Phase 1 brief |
| **L15** | **A green exit is not proof.** Run every check, read the output, and inspect the line for the thing you changed. Report what failed as plainly as what passed; if something cannot be verified, say so and name what would verify it. | "Zero contrast failures across 16 slides" was 40 failures including body text at 1.08:1 |
| **L16** | **The factory builds and reports; the owner approves, commits, publishes and installs.** Nothing is built until the gate table is approved. Published is not installed. | `HANDOFF` §10 *"Do not deploy"*; `course-tablet-publisher` §5 |

**What goes in `CLAUDE.md`:** L1–L5 and L14–L16 in one line each, plus a pointer to this file.
The rest are enforced where they bite — L6/L10 in the UX skills, L11/L12/L13 in their owning skills,
L7/L8/L9 in `CLAUDE.md` as a single "before you delete or regenerate" paragraph.

---

## 2 · REUSABLE PROCEDURE — Skill candidates

Consolidated. Where two responsibilities can cleanly belong to one skill, they do.

| Procedure | Skill | Status |
|---|---|---|
| Programme transcription, hours law, module split, the gate, build order, ILO immutability, ratio rule, outcome coverage, terminal contract, verification order, companion notes | `course-factory` | **exists, v1.1** |
| One-page module architecture, screen-inventory gate, audience routing via `data-cue`, run-script generation, the measurement floor and its traps | `course-module-ux` | **exists, v1** |
| The locked look: tokens, two modes, header band, cards, pills, photo, takeaway, semantic colour | `course-module-ui` | **exists** |
| Trainee task screens: what a task may contain, how a trainee answers, navigation, typed input, completion, the measurable floor | `course-task-ux` | **exists, v1** |
| Publishing to the two terminals and the shared repository: role separation, gates, registry, git rails | `course-tablet-publisher` | **exists, v1** |
| **Choosing the right representation for a concept, and designing instructional animation** — photo vs annotated photo vs schematic vs SVG animation vs interactive figure vs plain text; the named-engine pattern; "explain then show"; the drawing declaration | **`course-visuals`** (`design/` lane) | **NEW — the biggest hole** |
| **Sourcing a visual: the four-step hierarchy, provenance, licence, rights escalation, naming, format and size** | **`course-visuals`** (`source/` lane) | **NEW** |
| **Retrieving evidence from a Docling knowledge base with authority tiers and citation format** | **`course-evidence`** | **NEW — generalised from the project-local `gas-basic-kb-retrieval`** |
| Building the knowledge base from `source_files/` | already a script + recipe (`kb_builder.py`, `HOW_TO_BUILD_A_KNOWLEDGE_BASE.md`) — **stays a script**, not a skill | keep |
| The trainee handout | currently points at the org skill `novikontas-handouts` | **unresolved dependency — see D-3** |
| ILO wording, verbs, constructive alignment, assessment design | org skill `novikontas-pedagogy-toolkit` | **unresolved dependency — see D-3** |
| Logo, corporate colour, print identity | org skill `novikontas-brandbook` | **unresolved dependency — see D-3** |

### Why `course-visuals` is one skill and not two

They are never used apart. You cannot decide "annotated real photograph" without knowing whether such
a photograph can be sourced, and step 4 of the sourcing hierarchy — *create it* — **is** the design
lane. One skill, two lanes, one router, one token cost. If the source lane later grows a large rights
and licensing reference it can split; recorded so the split is a decision, not a drift.

### Why it must not be folded into `course-module-ui`

`course-module-ui` owns **chrome** — the palette, the typography, the component geometry. This owns
**content imagery**. Different decision, different failure mode (generic AI graphics rather than
visual drift), different verification (provenance and "does it teach" rather than a token audit).
Folding them would produce a skill nobody can describe in one sentence.

---

## 3 · ISOLATED SPECIALIST WORK — Agent candidates

Three. The bar is a real isolation benefit, not "this feels like a specialist".

| Agent | Why isolation genuinely pays | Risk |
|---|---|---|
| **`visual-sourcer`** | Bulk image research, licence checking and provenance writing is verbose, reads many pages, produces files plus one delivery report, and needs almost none of the main conversation. The golden course already ran it this way: `IMAGE_BRIEF.md` → a fresh session → `IMAGE_DELIVERY.md`, and it worked. Restricted tools; writes only into `assets/` and its report. | none material |
| **`evidence-retriever`** | Knowledge-base retrieval reads `content.md` files that exceed 1.4 MB. The playbook's own rule is *never read one whole*. An agent that answers **one** evidence question and returns a citation keeps the corpus out of the main context entirely. Read-only tools. | none material |
| **`module-producer`** | Building one module is a long, self-contained run. Parallel module agents were used on GAS BASIC and did deliver. | **This is how the visual drift happened.** Modules 3, 5 and 6 — a second token dialect, eight tokens missing, six values off — were produced by parallel agents. **Gate it:** fan out only after the visual system (build step 8) is frozen as one shared tokens file, preload the UI and UX skills, and run the UI audit per agent before merge. |

**Rejected as agents:** running the verification suite (the output must be read by the main thread, and
it is cheap); the hours/module-split work (it is the gate conversation with the owner); publishing
(rails, not reasoning).

---

## 4 · DETERMINISTIC PROTECTION — Hook / validator candidates

Split into two kinds. **Validators** are the seven existing scripts, invoked by skills at verify.
**Hooks** are the rules that must not depend on model compliance at all.

### Hooks — one `hooks/hooks.json`, six small scripts

| Event | Guards | Evidence it is needed |
|---|---|---|
| `PreToolUse` on `Write\|Edit\|NotebookEdit` | **deny** any write inside the reference course, `source_files/`, `knowledge_base/`, or the Android project outside an authorised publish | L14; the Phase 1 brief; `HANDOFF` §10 |
| `PreToolUse` on `Write\|Edit` | **deny** a write to a generated file (`it_run.js`, `courses/registry.js`, `gb_tasks.js`) with the message "regenerate instead" | L11; both files' own headers |
| `PreToolUse` on `Bash` | **deny** `git push --force`, a push to the app repo's default branch, and `git add -A` inside the app repo | `course-tablet-publisher` §4 — the working tree routinely carries a colleague's half-finished work |
| `PostToolUse` on `Write\|Edit` for `*.html` under a course or asset root | **warn** on: a remote script/stylesheet/font/image; a non-HTML navigation target; `target="_blank"` / `window.open`; `<input type="file">`; a page with no `gbt-topback` / `.gbn-back` / `gb-home`; an `<a href>` inside a `.slide` | Android contract 3.1–3.3; `course-module-ux` law 1 |
| `PostToolUse` on `Write\|Edit` | **warn** when a diff is much larger with whitespace than without — the signature of a bulk tidy that reformatted files it was not asked to touch | a tidy-up regex pass reached 37 files with no relevant content and stripped indentation before closing tags; all 37 had to be reverted |
| `Stop` | **inform** if course files changed this session and no verification script was run | L15 |

Nothing above blocks work the owner has explicitly authorised — the deny hooks read an
`allow_publish` marker the publisher sets, so publishing is possible and accidental writes are not.

### Validators — keep, do not multiply

`check_hours.py` · `check_syllabus_coverage.py` · `verify_course.py` · `verify_links.py` ·
`audit_navigation.py` · `crosscheck_tasks.py` · `audit_ui.py` · `check_task_pages.py` ·
`check_static.py` · `gates.py` · `registry.py` · plus the in-page probes `audit_deck.js`,
`audit_collide.js`, `audit_opacity.js`, `audit_drive.js`, `measure_in_page.js`.

**Every one of them was added after something got past the others.** Do not delete one because it has
not failed recently.

---

## 5 · REUSABLE IMPLEMENTATION — component and template candidates

| | |
|---|---|
| **Design tokens** | `tokens.json` + `gb_tokens.css` — pasted as a new deck's `:root`, never retyped |
| **Shared engines, one canonical copy each** | `gb_run` `gb_step` `gb_done` `gb_code` `gb_pin` `gb_phase` `gb_score` `gb_forms` `gb_observe` `gb_roster` `gb_return` `gb_kbd` `task_complete` `kbd_escape` — plus the terminal-root set `gb_nav` `gb_tasks` `gb_tablet` `gb_sync` `gb_identity` `gb_courses`. **Shipping one copy is itself a fix:** `gb_done.js` exists as five identical copies today |
| **Deck skeleton** | landing → progress → overview → cue → chrome → `<main id="stage">`, with the five-attribute slide contract |
| **Task page skeleton** | `gbt-topback`, sticky action bar with `env(safe-area-inset-bottom)`, explicit Submit, Correct/Partial/Incorrect + why |
| **Photo annotation pin system** | image-space `data-ix`/`data-iy`, crop-aware, self-hiding, edge-flipping labels |
| **Named visualisation patterns** | stepped-build cross-section · tap-a-card comparison grid · chips-onto-an-axis ladder · sourced curve with `~` on interpolated points · click-to-enlarge shared by deck and handout · wrap-up timer that never advances |
| **Data contracts** | `programme.json` (accredited hours table) · `plan.json` (module → topics → built minutes) · `syllabus.json` / `imo_coverage.json` · `course.json` (pack manifest) · `IT_MODULES` (instructor content, with a representable `gap` block) · `GB_TASKS` (tablet manifest) · `IT_RUN` (generated run script) |
| **Metadata schemas** | `_photo_meta.json` · `_figure_meta.json` · `_sim_meta.json` |
| **Documents** | `COURSE_BRIEF.md` · `factory-notes.md` · `DELIVERY_NOTES.md` · `task-notes.md` · the Advanced Module Plan structure (1–2 pages, no internal codes) · the image brief template |

---

## 6 · GOLDEN REFERENCE — pointers, never copies

Named by path, with what each demonstrates. **The factory repository holds pointers and cleared code
only.** No course content, no photographs, and never the ICS/SIGTTO figures.

| Reference | Demonstrates |
|---|---|
| `course/Module_01/presentation/index.html` + `.css` + `.js` | the canonical deck: slide contract, two modes, the five visualisation engines, the pin system, ES5 discipline |
| `course/Module_01/assets/photos/_photo_meta.json` | the provenance schema, filled in properly |
| `course/Module_01/assets/figures/_figure_meta.json` | the rights schema, including a `RIGHTS` block that blocks issue |
| `training_terminal/gb_nav.js` | building a whole navigation layer from a manifest, with lock states |
| `training_terminal/gb_courses.js` | one app, many courses, resolved synchronously and offline |
| `instructor_terminal/it_content.js` (header + schema) | instructor detail as data with provenance, and a representable gap |
| `instructor_terminal/it_run.js` (header + step kinds) | a generated run script and why it must stay generated |
| `_claude_working_area/IMAGE_BRIEF.md` | the best single reusable artefact in the project — the template for a self-contained specialist brief |
| `_claude_working_area/VERIFICATION_2026_09_07.md` | what an honest verification report reads like, including what it did **not** fix |
| `_claude_working_area/module_production_packs/SHARED_PRODUCTION_RULES.md` | the protected-baseline pattern |
| `course-factory-handover/FOR-YOUR-COLLEAGUE.md` | the tone the colleague-facing entry point must keep |

---

## 7 · ANDROID REQUIREMENT — integration contract

All of it is in `ANDROID_INTEGRATION_CONTRACT.md`. Summarised as constraints:
synthetic https asset origin · two allowed roots per flavour, merged at build · fixed MIME allowlist ·
HTML-only navigation · no `target="_blank"`, `window.open` or file input · every host except
`*.supabase.co` returns 403 · hardware Back is driven by `a.gbt-topback` / `.gbn-back` · no cache ·
ES5 · relative links only · everything under an asset root ships.

---

## 8 · GAS-BASIC-SPECIFIC — do not generalise

Listed in `GOLDEN_COURSE_EXTRACTION.md` §10. In one line: the 23 topics and their Latvian wording,
35/8/43 hours, the 40-minute academic hour, the six Main ILOs and 22 Sub-ILOs, the eight-module split,
36/26 assessment arithmetic, the `GAS1xx` codes, the Wärtsilä LCHS simulator, Dräger figures, the
ICS/SIGTTO/IGC corpus, the hazard tokens, and every photograph and figure.

## 9 · OBSOLETE — discarded

`oldversion/` · `_full_decks_2026-09-02/` · `test_area/` · `_to_delete/` · `_backup_before_fix/` ·
every `*.bak_*` · `Desktop/gas basic` · `tablet_package/` (stale by declaration) ·
`build_tablet_package.py` · `courses/gas_basic/module_01/` (removed 2026-09-07) ·
`gas-basic-module-ux` (superseded by `course-module-ux`).

---

## 10 · Contradictions found — named, not resolved

| | Contradiction | Recommendation |
|---|---|---|
| **C-1** | `SHARED_PRODUCTION_RULES` §H permits a Google Fonts `<link>`; `platform.json` calls a remote font a `WARN`; **the app returns 403** and the typeface never loads on the tablet. Three documents, three positions, one fact. | Bundle `woff2` + `@font-face`, or choose the system stack. Correct §H and `platform.json`. Raise the font check to `FAIL` for new courses only. |
| **C-2** | Teaching aid **A2** in programme §8.1 requires *"a theory presentation in Microsoft PowerPoint format"*; the system ships instructor-led HTML. Recorded as **R-10**, still open. | Owner/registrar decision. Meanwhile keep every graphic extractable so a PPTX visual-reference set can be produced. |
| **C-3** | **R-02** — several strong practical activities sit inside nominal *theory* hours. | Owner decision. The factory must never write anything implying the official classification changed. Already law (L3). |
| **C-4** | `delivery-contract.json` says the Android project is the single source of truth, but the **decks exist only in the desktop `course/` tree** and are not in either asset root. Neither tree is complete. | Decide where a deck lives and whether the tablet must be able to open it. See Android contract §6 and D-4. |
| **C-5** | `registry.js` header says *"Consumed by: nothing yet"*; `index.html` loads it and `gb_nav.js` reads it. | One-line fix at the next regeneration. |
| **C-6** | `FOR-YOUR-COLLEAGUE.md` tells a colleague to install **four** skills and omits `course-module-ui` — which `build-order.json` step 8 makes **required** for every new module. `install.ps1` installs all five. The documented path yields a factory that cannot perform its own mandatory step. | Fixed by moving to a plugin install; until then, correct the document. |
| **C-7** | `gb_tasks.js` was generated and is now hand-maintained, contradicting L11 and its own original header. | Either teach the generator the hand-made values (its header lists them) or declare the file authored and remove the generator. Do not leave it ambiguous. |
| **C-8** | The build order names `novikontas-handouts`, `novikontas-pedagogy-toolkit`, `novikontas-course-intake` and `novikontas-brandbook` as owners of required steps. **None of them is in the plugin**, and they reach this machine through a different distribution channel. A colleague who installs the course factory gets dangling references. | Decision **D-3** in the blueprint. |
