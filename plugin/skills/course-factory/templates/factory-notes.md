# <COURSE> — factory notes

*Written by `course-factory` during the run, into the course folder. Never left for a human to
fill in. This is the honest record of what was built, what was not, and what the next person
must check.*

**Run** <YYYY-MM-DD> · **Programme** <document, edition> · **Academic hour** <n> min

---

## 0 · Organisation skills — which route was taken

Owner decision **D-3**: the `novikontas-*` skills are not part of this plugin. One row per skill the
run touched. A run that records nothing here is a run that did not check.
Definitions and fallbacks: `org/ORG_DEPENDENCIES.md`.

| org skill | present? | route taken | what the fallback did not cover |
|---|---|---|---|
| `novikontas-pedagogy-toolkit` | yes / no | org skill / fallback F/B | |
| `novikontas-handouts` | yes / no | org skill / fallback F/C | |
| `novikontas-course-start` | yes / no | org skill / fallback F/A | |
| <any soft dependency the run touched> | | pointed at it / answered in-factory | |

## 0b · Language — COURSE_LANGUAGE

**COURSE_LANGUAGE:** `<English | Latvian | Norwegian | English+Latvian>`
**Determined from:** `<the existing course-facing files | the approved programme | the operator>`
**Drift check:** `check_language.py --declare <LANG>` → `<n course-facing files, 0 disagreements>`

The operator's language is separate and may differ. This report follows the operator; every slide,
task, handout, assessment, feedback line and instructor cue follows COURSE_LANGUAGE.

## 0c · Retrofit — only when the material already existed

*Delete this section when the course is being made from nothing, rather than from material that already existed.*

| | |
|---|---|
| **Classification** | `<A / B / C>` — score `<0.00>` from `classify_module.py` |
| **Signals that drove it** | `<shell 0.00 · composition 0.00 · visuals 0.00 · activity 0.00 · tablet 0.00 · tokens 0.00>` |
| **Re-classified after** | `<A / B / C>` — score `<0.00>` |

**Preserved — the content lock.** What survived and why. Technical meaning, programme requirements,
ILOs, hours, assessment intent, practical exercises, terminology, sourced facts, language.

**Rebuilt — the delivery.** What was replaced and why. Screens, order, layout, density, visual and
animation implementation, interaction, navigation, composition. *Name the weak implementation that
was discarded; "kept because it existed" is not a reason and must not appear here.*

**Representation upgrades.** Per screen: what is taught, what the learner should notice, what the
old representation was, what it became, and what the new one teaches that the old one did not.

**Waiting on a picture.** Every place a picture, drawing or photograph is still missing, what it
was needed for, and which screen is unfinished without it. Say what happens next for each one -
who finds it, or whether the factory should generate it.

**Screen count.** `<before>` → `<after>`, with the reason for each split, merge or addition.
Minutes unchanged at `<n>`.

## 1 · Hours — is it 1:1 with the programme?

| module | topics | allocated min | built min | diff |
|---|---|---|---|---|
| | | | | |
| **total** | | | | |

- `check_hours.py` verdict: **PASS / FAIL** (paste the verdict line)
- Fits the accredited days: **yes / no** — capacity <n> min, as built <n> min
- Topics outside the modules: <topic, hours, why>

## 2 · Moved to the handout

Class time is fixed by the programme, so anything that did not fit is self-study. Every item,
or the sentence "nothing had to be moved".

| item | from topic | minutes | where it landed |
|---|---|---|---|
| | | | |

## 3 · Practical ratio

- Target 80 %. **Achieved <n> %**, measured on allocated minutes.
- If below target: the programme's own table allocates <n> of <n> hours to practical, so the
  theory hours are delivered as **active learning**. Name the mechanism — the tablet task inside
  each theory block — and any theory block that does **not** have one, because that is a defect.

## 4 · ILOs

- Main ILOs: verbatim from the programme. **Count** <n>.
- Sub-ILOs re-expressed for digital or practical delivery: list each, with the original wording
  beside it. Every one is `PROVISIONAL` until the owner ratifies.
- Sub-ILO numbering shown to a trainee anywhere: **must be none**. Say so explicitly.

## 5 · What was produced

| artefact | where | note |
|---|---|---|
| modules | | screens per module |
| task pages | | codes |
| handout | | |
| assessment | | question count, pass mark, and where the pass mark comes from |
| module plans | the instructor tablet, `plans/` folder | one per module — if any module has none, say which |
| prepare material | the instructor tablet, `prepare/` folder | only modules whose practical needs a facility |

## 6 · Markers

Every one raised during the run, with its source, and what would close it. A marker used and not
reported here is the failure this section exists to stop - so for each one, say who answers it and
what happens to the course until they do.

| marker | what | source / why |
|---|---|---|
| `UNKNOWN` | | asked, operator did not know |
| `PLACEHOLDER` | | |
| `PROVISIONAL` | | |
| `[VERIFY: …]` | | |

## 7 · Verify list — what a person should check with their own eyes

Not everything can be checked automatically. Name the things that need a human to look, and be
specific about where to look and what right looks like:

- [ ] every numeric claim on a projected screen matches the page it points at
- [ ] each module's screens at every delivery size (projector and tablet)
- [ ] the instructor can go Start → Next to the end without hunting for anything
- [ ] a task the deck announces opens on the trainee tablet under the same name
- [ ] <course-specific>

## 8 · What was NOT done

Gaps, and why: waiting on a picture, waiting on somebody's decision, or outside what was asked
for. For each gap say what it means for the class and what would close it - an unreported gap
becomes a surprise in a classroom. Where the factory can close it, offer to.

## 9 · Feedback on the skill

*The improvement loop. Read this at the next revision; it is the only channel through which real
use reaches the skill.*

- Which step was slower than it should have been, and what would have made it faster
- Anything the skill asked that it could have derived
- Anything it derived wrongly
- A rule that turned out not to apply to this course, and why
