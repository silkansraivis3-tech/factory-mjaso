# Course production process

**How a course is actually made.** Reconstructed from the GAS BASIC record, generalised, and
corrected where the record shows the order was wrong.

Phase 1 · 2026-09-10. This is the process the factory automates; the blueprint says which skill owns
each step.

---

## The shape

```
INTAKE        source_files · knowledge base · the approved programme · a sentence from a colleague
   ↓
BASELINE      programme transcribed · model-course syllabus transcribed · ILO map
   ↓
ARCHITECTURE  module split · minutes · method per outcome · ratio
   ↓
█ GATE █      one table, approved by the owner. Nothing is built before this.
   ↓
PRODUCTION    screen inventory → visual system → visual plan → tasks → screens
              → handout → assessment → module plans
   ↓
DELIVERY      course pack into the terminals · run script regenerated · registry
   ↓
VERIFY        seven checks, output read, not asserted
   ↓
HANDOVER      companion notes · branch and pull request · owner installs
```

Three orderings are not negotiable, and all three were learned by getting them wrong:

- **The gate before anything is built.** Changing a table row is free; changing eight built modules is
  not.
- **The visual system before the first screen.** Retro-fitting tokens onto a finished deck is how
  drift gets signed off — three of eight shipped modules prove it.
- **Task pages before the deck announces them.** A screen announcing a task the tablet lacks is the
  worst failure in the room.

---

## 1 · Intake

The colleague provides four things and types one sentence.

| | |
|---|---|
| `source_files/` | the original documents, in category folders — the folder name becomes the source's authority level |
| `knowledge_base/` | the Docling extraction, built by `kb_builder.py`, with `00_INDEX/` |
| the approved programme | **the one blocking requirement.** No programme, no hours law and no ILOs |
| a normal-language brief | "make it highly practical", "Module 3 needs an interactive transfer exercise", "we use the LNG simulator, no live fire" |

Ask only for what is genuinely absent, batched two to four questions at a time. **Never ask** for the
module split, the screen count, the task codes, the pass marks or the file layout — those are derived,
and deriving them is the factory's job. Never web-search during intake: not in the brief, the
programme or the knowledge base means `UNKNOWN`.

`new-course.ps1` scaffolds the project. It is safe to re-run.

---

## 2 · Baseline — read the programme, not a copy of it

**Read the hours table from the original programme document, never from the knowledge base.** That
rule was set on GAS BASIC and it still holds: an extraction can lose a row.

Produce, in order:

1. **`programme.json`** — the accredited topic/hours table, the academic-hour length read off the
   programme (GAS BASIC: 40 minutes — never assume 60), the total row, and reconcile the transcription
   against that total.
2. **The model-course syllabus** — one row per item of its *Knowledge, Understanding and Proficiency*
   column, in its own numbering and **its own wording**. Transcribe; never summarise. These are the
   itemised outcomes the programme's topics only summarise.
   *Why this step exists:* on GAS BASIC the topic record was green at 64/64 and the model course had
   **never been checked**. Its 286 rows contain 266 real outcomes, and one of them was genuinely
   missing from the course.
3. **The ILO map** — Main ILOs verbatim and frozen; Sub-ILOs may be re-expressed for digital or
   practical delivery, each marked `PROVISIONAL`, none renumbered anywhere a trainee can see.

Expect the transcription to be messy. Model-course PDFs carry tracked-changes damage
(*"DescribesExplains"*, *"fFlammable vVapours"*), figure captions posing as outcomes, and American
spelling against a British-spelling course. Fourteen of the 32 unmatched items on GAS BASIC could
never have matched by string. **Read the residue by hand, searching for the concept.**

---

## 3 · Architecture — method chosen from the outcome backwards

For every ILO / Sub-ILO, in this order:

1. Can the trainee learn and demonstrate this on the **simulator**?
2. If not, can **real equipment** or **practical work** teach it?
3. If not, a realistic **scenario** or **case study**?
4. **Document work** — data sheets, permits, checklists — or collaborative problem solving?
5. An **interactive digital activity**?
6. Is explicit instructor **explanation** required?
7. Only then: does a presentation add genuine learning value?

Do not force the order when another method is pedagogically better. The target is not "no
presentation" — it is **no unnecessary presentation**. Some modules legitimately need none: on GAS
BASIC, four modules carry NO PPT and one is optional. For those, a minimal instructor screen set of
about six screens is permitted — opener, outcomes, activity launch, answers and discussion, debrief,
check briefing — and **no theory slides**.

Then group topics into teaching modules, sum each module's allocated minutes, and declare the topics
that sit outside the modules (a final assessment usually does).

**Determine the learner from the sources, not from habit.** A Basic course needs foundations, visual
explanation, terminology support and scaffolding. An Advanced course needs complex scenarios,
troubleshooting and integrated decision-making. Every module brief should carry a **DO NOT TEACH**
boundary.

Apply constructive alignment throughout: ILO → required performance → teaching activity → practice →
assessment evidence. Assessment must test the outcome, not attendance.

---

## 4 · The gate

Present **one table** and stop.

| | |
|---|---|
| **Programme** | document, edition, academic-hour length, total hours (theory / practical) |
| **Module split** | module → topic numbers → allocated minutes, the column summing to the programme total |
| **Ratio** | practical % achieved, and where active learning carries the theory if under target |
| **Per module** | screen count, task codes, the module check, whether a practical needs a facility |
| **Markers** | every `UNKNOWN`, `PLACEHOLDER`, `PROVISIONAL`, `[VERIFY: …]` raised so far |

`check_hours.py` must exit 0 before the table is believed.

**The one distinction that must never blur:** the *official hour classification* is an administrative
fact and is not the factory's to touch. The *learner experience* — what a trainee is doing minute to
minute — is what the factory designs. A nominal theory hour may legitimately be spent on a simulator
briefing, a document exercise or a tablet activity. Never write anything implying the official hours
changed.

---

## 5 · Production

### 5.1 Screen inventory, per module

One row per screen: number, screen, kind, block/minutes, activity code, what is on it, what cue moved
off it. **Every row of the timetable must appear.** A block with no row is the defect that silently
dropped 90 of one module's 220 minutes — and the table is the only place it is cheap to notice.

There is **no canonical screen count.** Ten screens, twenty-five, fifty, almost none, practical-only —
all legitimate. Never add filler to resemble the reference module numerically, and never cut real
teaching to resemble it either.

### 5.2 Visual system — before the first line of HTML

Paste the token set as the deck's `:root`. Every colour, radius, shadow and font in new work comes
from a token. A raw colour on `fill`/`stroke` inside a diagram is *content* and stays raw.

### 5.3 Visual plan — the step the golden course did last and should have done here

For each important concept, decide the representation, then source or create it. GAS BASIC ran this as
a separate late pass (`IMAGE_BRIEF.md` → a fresh session → `IMAGE_DELIVERY.md`) and found four modules
with **no content imagery at all** — every visual an inline SVG line drawing.

That late pass worked, and the brief it produced is the best reusable artefact in the project. But the
lesson is that the visual plan belongs **with the screen inventory**, not after the screens exist. The
sourcing *execution* can still be a separate isolated run.

The four-step hierarchy: `source_files/` and supplied assets → the factory's approved library → the
internet (CC0 / CC BY / CC BY-SA / public domain, preferring manufacturers, official organisations and
recognised maritime sources) → create it (SVG, HTML/CSS/JS, Canvas, or an image-generation MCP when a
real illustration is genuinely needed).

Use **real photographs** wherever a trainee must recognise something in real life. Use a **realistic
illustration or animation** only for what no camera can see — inside a containment system, a vapour
cloud travelling, a flammable range, the pipework of a fixed installation. A cutaway is often the right
answer: photograph the outside, illustrate the inside, and say which is which.

### 5.4 Task pages, then screens

Task pages first, always. Then the deck, which **announces** a task and never launches it.

Vary the mechanics deliberately across the course: hotspot, sort, sequence, match, slider, document
extraction, form completion, choose-and-justify, spot-the-error, scored multiple choice. Neighbouring
modules should not repeat one.

### 5.5 Handout — the overflow valve

One handout per module (or one per course, as GAS BASIC ended up), and **not a copy of the
presentation**. Three jobs: self-paced learning before or between sessions; reference during class;
review before the final test.

**Anything that will not fit the accredited minutes becomes self-study in the handout, and every moved
item is recorded with its source topic.** Class time is fixed; the handout is where the overflow goes.

What must not be duplicated from the deck: its narrative sequence, its instructor-facing framing, its
activity-launch and answer screens, its live classroom interactions.

### 5.6 Assessment, and module plans

The final assessment is separate from every module check and uses the programme's own question count
and pass mark. No answer key on a trainee page. A re-sit needs a different paper.

The Advanced Module Plan is the instructor's document and must be **compact — one to two pages**. It
is not a teaching script. Purpose · ILOs in approved wording · total time and the day · before-class
setup · the teaching flow block by block (time, instructor action, trainee action, material, learning
evidence) · activity and simulator points · the module check and its pass evidence · remediation ·
the few debrief points that must be said out loud. **No internal codes, no chunk numbers, no QA
metadata.** Those live in the working area.

---

## 6 · Evidence discipline, running throughout

**NO SOURCE = NO MARITIME CLAIM.** Never fill a gap from model memory. A stated gap is a good answer.

Authority tiers, never upgraded: approved programme → mandatory instruments → model course (check
whether it is a draft) → conventions and codes → own-equipment manuals → industry guidance → legacy
course material, design reference only.

Escalate only when a level genuinely fails: knowledge-base chunks → a bounded line range of the matched
`content.md` (some exceed 1.4 MB; never read one whole) → the original in `source_files/`, read-only →
external, labelled `EXTERNAL — NOT FROM KNOWLEDGE BASE` with organisation, title, URL, date, the claim
it supports, and why the knowledge base was insufficient.

Check every source's **edition on its own cover page** before quoting it.

Classify every claim `GREEN` / `YELLOW` / `RED`. A `RED` item blocks the affected statement, not the
module. Use exactly four honesty markers — `UNKNOWN`, `PLACEHOLDER`, `PROVISIONAL`,
`[VERIFY: <what to check>]` — and **every marker written into an artefact must also appear in the
companion notes.** A marker used and never reported is the failure the rule exists to stop.

---

## 7 · Delivery and verification

Course pack into the trainee terminal; plans, prepare and record into the instructor terminal;
regenerate the run script and the registry. **No app code, no forked terminal, no copied shared
engine.**

Then run all seven checks and **read the output**:

`check_hours.py` · `check_syllabus_coverage.py` · `verify_course.py` · `verify_links.py`
(merged asset root) · `audit_navigation.py` · `crosscheck_tasks.py` · `audit_ui.py --strict`
(new modules only), plus the in-page measurement lane in a real engine.

Two traps: a clean report can be false (a 0.42 s CSS transition produced "zero contrast failures"
where there were 40, including body text at 1.08:1), and a green exit is not proof the work happened —
inspect the line for the thing you changed.

---

## 8 · Handover

Write the companion notes into the course folder: what was produced, every marker with its source, the
achieved practical ratio, what moved to the handout and why, what could not be verified, and feedback
on the factory itself.

Then stop. **The factory builds and reports; the owner approves, commits, publishes and installs.**
Published is not installed — reaching the shared repository does not put a course on a tablet.

---

## 9 · Working habits that survived contact with the work

Short, and each one is a rule somebody had to be told twice.

- **Edit, do not regenerate.** Freeze stable artefacts and patch them with scripts.
- **Explain and relocate; do not delete.** "Why is this here?" is a report about the presentation.
- **Grep before you remove anything.** Three of four "useless" findings were load-bearing.
- **Visible must be sufficient, not merely short** — and if a visible line refers to something, name
  that something on the same line.
- **Plain language is for navigation only.** Buttons, labels, step cards and instructions get simple.
  Teaching prose keeps full professional register; maritime terminology is never softened.
- **Never bulk-tidy whitespace.** A regex pass reached 37 files that had no relevant content and
  stripped indentation before closing tags. All 37 had to be reverted.
- **Internal files never enter a human-facing course folder.** QA logs, evidence notes and machine
  metadata live in the working area.
