# Golden course extraction

**What GAS BASIC actually is, how it was produced, and which parts of it are reusable.**

Phase 1 · 2026-09-10.

Reference course (read-only): `C:\Users\raiviss\Desktop\docling\gas_basic\GAS Basic`
Delivered course (read-only): the two asset roots in `NOVIKONTASTraining`

> The maritime content of GAS BASIC was **not** audited and is not in scope. This document extracts
> the production system and the design language, not the subject matter.

---

## 1 · The five places one course lives

This is the first thing to understand, because it explains most of the friction in the project.

| Tree | What it holds | Authority |
|---|---|---|
| `source_files/` | the original PDFs, in four category folders | **read-only, never touched** |
| `knowledge_base/` | the Docling extraction of those PDFs, plus `00_INDEX/` | derived, searchable |
| `_claude_working_area/` | briefs, evidence, QA, coverage scripts, generators, checkpoints | **internal — never ships** |
| `course/` | the human-facing course: 8 modules, decks, handouts, plans, START_HERE | authoritative for what the course **says** |
| Android `app/src/**/assets` | the two terminals | authoritative for what **ships** |

`delivery-contract.json` states the rule: *the Android project is authoritative; any Desktop copy is a
working area and diverges silently.* In practice **neither tree is complete** — the decks exist only
in `course/`, and the tablet's task manifest has drifted from the deck it was generated from.
`tablet_package/` on the Desktop is explicitly marked stale; do not edit it.

**Reusable rule:** one course, one authoritative tree per artefact class, and a named generator
between them. A course that is authored in one place and shipped from another needs the copy step to
be a script, not a habit.

---

## 2 · The folder architecture that works

Per module, in the authoring tree:

```
Module_0N/
  START_HERE.html        the instructor's timed pre-flight - one button
  presentation/          index.html + presentation.css + presentation.js
                         + gb_answers.js / gb_review.{css,js}   (INSTRUCTOR-ONLY)
  tasks/                 the trainee task pages + tasks.css/.js + index.html
  handout/               index.html + handout.css + handout.js
  assessment/            module check, criteria, printable paper, skills record
  instructor_guide/      ADVANCED_MODULE_PLAN_MN.html  (1-2 pages, compact)
  documents/             reference cards a trainee keeps
  simulator/ practicals/ briefs, task cards, debrief prompts, fallbacks
  assets/
    photos/   + _photo_meta.json      real photographs, CC-licensed
    figures/  + _figure_meta.json     drawings, cutaways, publisher figures
    brand/                            logo SVG, doc.css, silhouettes.js
    gb_*.{css,js}                     the shared interaction engines
```

Two things in that layout are the load-bearing ideas, and both are reusable:

1. **Role is expressed by folder, not by convention.** `instructor_guide/`, `gb_answers.js`,
   `*_criteria.html`, `*_paper.html` are separable by pattern, which is what makes the publisher's
   trainee/instructor gate mechanical rather than a judgement call.
2. **Every asset folder carries a provenance file beside the files.** Not a central register that
   goes stale — a `_photo_meta.json` in the same directory as the JPEGs.

---

## 3 · The deck: one page, Start, Next to the end

`Module_01/presentation/index.html` is 98 KB of HTML, 90 KB of CSS, 54 KB of ES5 JavaScript, no
dependencies, no build step, no CDN.

```html
<body data-gb-key="m1" data-next-module="…" data-next-label="…">
  <div id="landing">      Start presentation · keyboard legend
  <div id="progress">     <div id="overview">   <div id="cue">   <div id="chrome">
  <main id="stage">
    <section class="slide dark" data-block="Block A1" data-kind="Opening"
             data-title="…" data-foot="…" data-cue="…">
```

### The slide contract

Every slide carries **five** attributes, on all 27 slides without exception:
`data-block` · `data-kind` · `data-title` · `data-foot` · `data-cue`.

That consistency is what makes the run script generable. `gen_it_run.py` derives the instructor's
running order from the deck's own markup — step kinds `talk` / `task` / `activity` / `sim` / `group` /
`check` / `day` — so a slide number can never be wrong by hand.

`data-kind` is the screen taxonomy actually used in the golden module, and it is a good default set:

`Opening` · `Block opener` · `Orientation` · `Theory` · `Visual explanation` · `Real life` ·
`Interactive` · `Live activity` · `Go to the tablets` · `Simulator orientation` · `Summary` ·
`Hand-off` · `Module check`

Five of 27 are `Theory`. That is the 80/20 rule visible in markup.

`data-cue` is the **instructor-only channel** — never rendered, revealed on the instructor's own key.
It is why the audience rule costs nothing: instructor craft is *routed*, not deleted.

### Two slide modes, chosen per screen

`.slide` is light; `.slide.dark` and `.slide.photo` are dark. A photo screen is always dark so the
image is not framed in white. This is not a theme toggle — both live in one deck. Every colour that
touches text therefore exists twice (`--dim-l` / `--dim-d`, `--good` / `--good-d`, …).

### Mechanics that must carry forward

- `START PRESENTATION` from a landing screen; `EXIT` returns to it; fullscreen classroom mode
- `NEXT` / `BACK` — **manual instructor pacing only. Nothing auto-advances, ever.**
  A wrap-up timer may display and must never advance a slide.
- Keyboard: → ← Space PageUp PageDown F G N Home End, with a `keyCode` fallback
- Touch/swipe, guarded so a swipe inside an interactive element does not turn the page
- Slide counter, progress bar, and a grid overview (`G`)
- **Zero `<a href>` inside a slide.** A link inside a delivery screen is the old multi-page model
  leaking back in.
- The deck **announces** a task; it never launches it. (The launch buttons in Module 1 predate the
  rule and are dead on the tablet anyway — see the Android contract, section 3.1.)

---

## 4 · The visual system

### Tokens (from `presentation.css :root`, Module 1 — the canonical reference)

Navy `#0A2463` · deep navy `#0A182E` · screen blue `#2EB6F8` · steel `#415C8F` · amber `#E9A51E`
(accent only, never body text) · white cards · ink `#011111`.
Paired for the two modes: `--txt-d` `--dim-l/-d` `--faint-l/-d` `--line-l/-d` `--blue-wash-l/-d`
`--amber-wash-l/-d` `--good/-d` `--warn/-d` `--sh/-sh-d`.
Radii `--r-l:20px --r-m:13px --r-s:8px`. Type: Raleway with a real system fallback stack.

Two token values carry a measured justification in a comment — `--amber-ink` was darkened from
`#B87F0C` after measuring 3.45:1 on white, and `--faint-l` became brandbook Steel Blue after
measuring 3.58:1. **Measured, with the number, in the file.** That habit is worth keeping.

### Measured drift — the reason a visual skill exists

Across the eight modules, measured 2026-09-09:

- Modules **04, 07, 08** match Module 1 exactly
- Modules **03, 05, 06** run a second dialect: `--blue-soft-*` instead of `--blue-wash-*`, eight
  tokens missing, six values off by a shade, and three tokens the reference lacks (`--red`,
  `--flame`, `--toxic`)
- Two `gb_review.css` files declare no `:root` at all
- `presentation.css` itself carries **134 raw chrome colours, 81 distinct**, outside its own `:root`

The drift correlates with parallel module production by separate agents. **This is the single most
important production lesson in the project:** a UX floor (contrast, tap size, overflow) does not
produce a consistent look. Two workers can pass every floor check and ship modules that look
unrelated — and they did.

### Instructional visualisation — the part that is genuinely good

Module 1's engine defines five named visualisations, each with its source cited in the code:

| | What it does | Source cited in code |
|---|---|---|
| G1 | liquid → vapour expansion, animated | SIGTTO LGHP4 §2.8.6 Table 2.10 |
| G2 | ship cross-section, **stepped build** from the sea inwards, two containment modes | — |
| G3 | containment comparison grid, tap a card to enlarge | — |
| G4 | boiling-point ladder, chips drop onto a temperature axis, collision-free lanes | SIGTTO LGHP4 Table 1.1; IGC 4.5 |
| G5 | temperature ↔ pressure curve, drawn through **four sourced values only**, interpolated points shown with `~` so nothing invented is presented as measured | four cited values |

Plus a **photo annotation pin system**: pins are positioned in *image* coordinates
(`data-ix` / `data-iy` as a percentage of the photo) and mapped through the `object-fit: cover` crop,
so they stay on target at any aspect ratio. A pin whose target is cropped away hides itself; a pin
near the right edge flips its label. **The annotation is live HTML/SVG, not baked into the image**, so
it survives any crop, and a replaced photograph does not invalidate the teaching.

19 CSS `@keyframes` exist, and every one animates a mechanism or a state change — vapour drift,
mercury rising, a needle moving, a fleet crossing, a tap-press acknowledgement. None is decoration.

**Reusable principles:**
- Explain first, *then* show. When text and animation compete for attention, split them across two
  screens.
- A visualisation is a named engine with a cited source, not a div with a transition.
- A generated value inside a sourced chart is marked (`~`) rather than presented as measured.
- Annotations live in image space, in the DOM.
- Every drawing declares on its face that it is a drawing ("This one is a drawing, not a photograph,
  because half of what you are asked to find is inside the hull").

---

## 5 · The asset pipeline, as it was actually run

`_claude_working_area/IMAGE_BRIEF.md` → a separate session → `IMAGE_DELIVERY.md`. The brief is the
best single artefact in the project to generalise: it is self-contained, states what the job is
*not*, fixes naming, format and size, fixes the licence rule, fixes the metadata schema, gives a
prioritised shot list, names what must stay a drawing, and ends with two escalation rules.

The hierarchy it encodes:

1. **Verified real photograph** — wherever a trainee must recognise something in real life
2. **Annotated real photograph** — pins in image space, never baked in
3. **Realistic infographic / animation** — for what no camera can see
4. **Technical interactive schematic**
5. **Simple vector** — only when genuinely sufficient

Hard rules that came out of real failures:

- **Photographs: CC0 / CC BY / CC BY-SA / public domain only.** Not CC BY-NC, not CC BY-ND, not
  "free to use", not stock previews, not scraped from a manufacturer site or a PDF.
- **Open and look at every file before using it.** A Wikimedia file named "Arctic Princess LNG
  carrier" turned out to be a small red general cargo ship. `visually_verified` must say `yes` and
  give the date, or say plainly that it was not verified.
- **Never a misleading AI pseudo-photograph of safety-critical equipment.** A trainee who learns to
  recognise a gas detector from a plausible invention has learned something false.
- **Never contradict named kit.** The module quotes Dräger figures, so the tube shots must be Dräger
  with an `accuro` pump — and a colorimetric tube whose make is not identifiable must not be captioned
  as Dräger.
- **Caption honestly when the shot is a near-miss.** "abandon-ship muster, not a fire muster";
  "product tanker, not a gas carrier"; "generic radios, not ATEX — must not claim intrinsic safety".

`_photo_meta.json` schema, per file: `commons_title` `page_url` `author` `license` `license_url`
`credit` `description` `date_original` `orig_size` `downloaded` `stored_size` `teaching_purpose`
`used_in` `visually_verified`.
`_figure_meta.json` for a generated drawing: `origin: generated illustration` `generated_by`
`depicts_what_no_photograph_can`; for an extracted publisher figure: `source_document`
`authority_tier` `figure` `caption_in_source` `section` `page` `shows` `extracted_from`
`how_identified` `visually_verified` **`RIGHTS`**.

> **The rights problem is real and unresolved.** Six ICS/SIGTTO figures in Module 1 are marked
> *"NOT cleared for issue or publication"* and **currently block the course from being issued**.
> They must never enter the factory repository.

**Known limitation, still true:** 5,308 figures were extracted from the source corpus, but every
`![Image](...)` link in `content.md` points at a stale Windows temp path and no chunk carries an image
reference. Reusing a knowledge-base figure means a manual caption-search-then-folder-match. The KB
visual pipeline has **not** been fixed; the working route is verified photographs plus purpose-built
inline SVG.

---

## 6 · Trainee task screens

Tablet-first, touch-first, offline, no runtime dependency. Large controls, minimal typing, explicit
Submit, Correct / Partial / Incorrect, and **always an explanation of why** — the feedback teaches, it
does not merely score.

**Varied mechanics, deliberately.** Across the course: identify-on-image / hotspot, sort into
categories, order a sequence, match pairs, slider or dial estimation, read-a-document extraction,
complete-a-form, choose-and-justify, spot-the-error, scored multiple choice. Neighbouring modules must
not offer the same mechanic.

Activity codes are per module (`GAS101`, `GAS201`, …) and each is registered in a small metadata
object on the page (activity code, `futureTaskId`, the selector of its answer slide) so a live task
backend can be attached later without touching content.

The class flow pattern:

```
ACTIVITY-LAUNCH SCREEN  →  individual tablet task  →  instructor waits, no auto-advance
                        →  ANSWER / DISCUSSION SCREEN  →  continue
```

Page shape, from a real task:

```html
<script src="../../../gb_config.js"></script>
<script src="../../../gb_sync.js"></script>
<link rel="stylesheet" href="task.css">
<link rel="stylesheet" href="../../../gb_nav.css">
<link rel="stylesheet" href="../../../gb_tablet.css">
<body>
<a class="gbt-topback" href="../../../index.html#m3">◀ Back to Module 3 tasks</a>
```

`gbt-topback` is not cosmetic — it is the hook the Android hardware Back button clicks.

---

## 7 · Shared engines

Present in every module's `assets/`, and the reason the modules behave alike:

`gb_run` (step runner) · `gb_step` · `gb_done` (completion) · `gb_code` (activity code entry) ·
`gb_pin` (photo annotation) · `gb_phase` · `gb_score` · `gb_forms` · `gb_observe` (observed criteria) ·
`gb_roster` (per-trainee marking) · `gb_review` + `gb_answers` (answer reveal — **instructor-only**) ·
`gb_return` · `gb_kbd` (keyboard escape).

At the terminal root: `gb_nav` · `gb_tasks` · `gb_tablet` · `gb_sync` · `gb_identity` · `gb_config` ·
`gb_courses` · `radar` · `style.css`.

> **They are duplicated.** `gb_done.js` exists as five identical per-module copies. A copy goes stale
> the first time the engine is fixed. The factory must ship **one canonical set** at the terminal root
> and forbid copies into a course pack.

---

## 8 · The instructor terminal — content as data

`it_content.js` is **429 KB of course content as a JavaScript data structure**, and
`run/index.html` renders every page from it. Nothing is hand-written in HTML, so the pages follow the
data.

```
IT_MODULES = [ { key, n, title, short, label, eyebrow, oneline, duration, status,
                 facts: ["chip", …],
                 sections: [ { id, title, tab, kicker, desc, foot, state, todo,
                               blocks: […] } ] } ]
```

Its header names, per block, the source every duration, threshold, criterion and procedure was copied
from — and states the discipline: *"NOTHING IS INVENTED. Where a source gives no figure the block says
so — a `t:"gap"` block, or `dur` left out so the run sheet prints 'Duration not documented'. Do not
replace either with a plausible number."*

**This is the strongest reusable idea in the instructor half of the system**: instructor detail is
data with provenance, rendered by one renderer, and an absence is representable.

---

## 9 · Verification, and why each check exists

Seven scripts, and **every one was added after something got past the others.**

| Check | Question it answers | What got past everything else |
|---|---|---|
| `check_hours.py` | are the built minutes 1:1 with the accredited programme? | the course was built to 2175 minutes against an accredited 1640 — a 33 % overrun found only after all eight modules existed |
| `check_syllabus_coverage.py` | is every **itemised** model-course outcome taught? | the topic record was green at 64/64 and had never been checked against IMO 1.04's 266 itemised outcomes, where one real gap sat (9.2.7, decontamination showers and eyewash) |
| `verify_course.py` | structure, counts, check → hand-off order | |
| `verify_links.py` | does every link resolve **in the merged asset root**? | 1345 links, 0 dead — while a whole section was invisible |
| `audit_navigation.py` | is every page **reachable**, and does it have a way back? | 28 pages — every safety brief, rotation plan and practical write-up — sat behind an index nothing linked to, with `verify_links.py` green |
| `crosscheck_tasks.py` | do deck, run script and tablet manifest agree? | a screen announcing a task the tablet lacks is the worst failure in the room |
| `audit_ui.py --strict` | does a **new** module use the reference token set? | three modules had already started a second visual dialect |

Two measurement traps, both recorded from real incidents:

- **A clean report can be false.** "Zero contrast failures across all 16 slides" was actually 40
  failures including body text at 1.08:1 — the cause was a 0.42 s CSS transition still running when
  the measurement was taken.
- **A green exit is not proof the work happened.** Read the line for the thing you changed.

---

## 10 · What is GAS-BASIC-specific and must not be generalised

Everything here is subject matter or one course's arithmetic. None of it belongs in the factory.

- The 23 official topics, their Latvian wording and their order
- 35 theory / 8 practical / 43 total; the 40-minute academic hour; 11 slots a day; four days
- The six Main ILOs and 22 Sub-ILOs, and the 2026-08-27 SME wording round
- The eight-module split and the topic→module mapping
- 36 questions / 26 to pass / one retake with a different variant
- Activity codes `GAS1xx`–`GAS7xx`, `RUN_CODE = "GAS101"`
- Wärtsilä LCHS TechSim LPG Tanker Generic v1.0 as the only permitted simulator
- Dräger figures, the ICS/SIGTTO/IGC/MARPOL corpus, `gas-basic-kb-retrieval`
- The `--red` / `--flame` / `--toxic` hazard tokens (a gas course's need, not every course's)
- Every photograph and figure in `Module_0N/assets/`

## 11 · Obsolete — discarded

`course/oldversion/`, `course/_full_decks_2026-09-02/`, `test_area/`, `_to_delete/`,
`_backup_before_fix/`, every `*.bak_*` file, `Desktop/gas basic` (an earlier project root),
`tablet_package/` (explicitly stale), `build_tablet_package.py` (its own output warns that running it
reverts hand-made corrections), and `courses/gas_basic/module_01/` (100 files of the abandoned
"courses as data packs" prototype, removed 2026-09-07).
