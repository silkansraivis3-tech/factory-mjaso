# Simulators — every item a simulator can train is trained on one (L66)

Read this lane for every **advanced** course (Oil, Chemical, Gas, IGF Advanced) and for any course whose programme
names a simulator. It runs **unasked**, at Stage 2, after the model course's syllabus is transcribed (build order step
2) and the old course is read (step 4b), and **before the gate** - the gate's practical tasks are planned from it.

    python coverage/scripts/sim_coverage.py needed <course>      does it apply, and which simulators
    python coverage/scripts/sim_coverage.py init   <course>      one empty row per syllabus item
    python coverage/scripts/sim_coverage.py check  <course>      whole, or what is missing (exit 2)

The school's simulators cost hundreds of thousands and are used to the maximum: the course is as practical as the
school's equipment allows. A simulator task may be **on paper** - the trainee card printed and laminated, the
instructor grading from the instructor sheet (grading on the instructor's tablet comes later). The ILOs and the
module hours never change for a simulator task: its minutes come from inside the module.

The worked example is IGF Advanced (`coverage/knowledge/simulators.json` → `courses.igf-advanced.worked_example`):
332 items of MC 7.14 against three simulators, 69 COVERED, 43 PARTLY, 18 GAP, 202 NOT-SIM - the biggest gap was fire,
which two simulators model and no exercise used.

---

## 1 · Which simulators

`coverage/knowledge/simulators.json` lists the school's simulators, their manuals (file name, page count, where pages
are counted from) and which advanced course trains on which. `needed` picks the course's set from the programme's title;
`intake.json` → `"simulators": ["LNG", "MeOH"]` overrides it. The manuals are on
`G:\My Drive\Gas Library\documents\manual\` (copies of 2026-10-23 in `G:\My Drive\_staging Gas Library 2026-10-23\`);
they are INSTRUCTOR_ONLY sources - read, cited by page, never copied into a trainee page. A simulator or manual not in
the file is added there (a factory change), so the next course finds it.

Whether a model is installed, and which options it has (e-Tutor, fault injection, saved states, time compression), is
**checked with the course director, never assumed** - such things go in the decisions list (§5), not into a verdict.

## 2 · SIM_MAP.md — what each simulator can do, from its manuals

`course\working_claude\SIM_MAP.md`. Per simulator: the prototype (plant, tanks, pressures), the procedures and
scenarios with their step lists, the instructor-injectable faults, the shutdown and ESD logic, the alarms and detectors,
the 3D and CCTV scenes, what a trainee can read for a calculation - **every fact with its manual and PDF page**
(`LNGBunk p62`). Then what the manuals do not say (no fault list, no durations), and estimated durations marked as
estimates. One agent per manual reads it (orchestration, Rule 1); the map is written once and shared.

## 3 · SIM_COVERAGE.json — one row per syllabus item

`init` writes the rows from the transcribed syllabus (`*syllabus*.json`): every leaf Knowledge / Understanding /
Proficiency item - a line that only introduces its children ("such as:") is not an item. Each row gets one verdict:

| Verdict | Means | The row must say |
|---|---|---|
| **COVERED** | the simulator trains or assesses it, and an exercise does it on the simulator now | `sim`, a manual page, `covered_by` |
| **PARTLY** | it can, and the course touches it - in part, on paper, as an option or on one simulator only | the same |
| **GAP** | it can, and no exercise does | `sim`, a manual page, and a proposed task (§4) |
| **NOT-SIM** | it cannot sensibly be trained or assessed on these simulators | why, and what the course does instead (`note` or `covered_by`) |

Judge from the item's **verb** and from what the manuals **describe** the simulator doing. Where a simulator can only
*show* a thing (a 3D scene, a number) it is NOT-SIM with `sim_use: "illustrate"` - not a gap. Chemistry, the Code's
text, SDS, permits, SCBA and first aid are NOT-SIM; their practice is the lab, the mock-up or the paper exercise.
The schema is `coverage/knowledge/sim_coverage.schema.json`; `counts`, `counts_by_competence` and `total_leaf_items`
are the rows' own counts.

## 4 · The GAP tasks — proposed, then drafted as exercises

Every GAP item goes into a **proposed task** (`proposed_tasks`, ranked by value): its simulator, the items it trains,
the module, the minutes and **where they come from inside the module's approved hours** (`minutes_from`: theory
minutes turned into simulator practice, or a paper part moved onto the simulator - net 0), the scenario, the faults to
inject, the manual pages, what must be checked on the installation (`needs`). An inject inside an exercise that already
runs has `"minutes": 0`. A PARTLY item belongs in a task too where one fits; one left is shown for review, not failed.

Every task that closes a GAP is **drafted as an exercise** - the existing exercise forms, a **Trainee** card and an
**Instructor** sheet (`novikontas-practical-exercises`; its content file
`working_claude\exercises\sim_drafts\MNN\content\EX_<no>.json`, the form's own fields, its honesty markers under
`_markers`) - rendered to `to_review\exercises\sim_drafts\MNN\<PREFIX>_Exercise_<no>_Trainee_DRAFT.docx` and
`..._Instructor_DRAFT.docx`. The task names it: `"draft": "<no>"`. An inject inside an existing exercise is drafted as
that exercise's amended forms, under its own number. The drafts are not the approved exercises: they are not built
into a module until the course director accepts them, and an approved exercise they would change is named, not edited.
Without the org skill installed, the content file is the draft and the review README says the forms are not rendered.

## 5 · SIM_COVERAGE.md and the review

`course\working_claude\SIM_COVERAGE.md` - how to read it, the headline counts (by verdict and by competence), what the
course uses the simulators for now, competence by competence, the old course's simulator tasks and where each lives
now, the proposed tasks, the simulator minutes now and proposed per module (`sim_minutes`), what a human must decide or
check, and the source conflicts. Beside the drafts, `to_review\exercises\sim_drafts\README_FOR_REVIEW.md`: the counts,
the drafts table (task, simulator, module, minutes, where from) and the decisions for the course director - asked as
**one pop-up** at the Stage 2 STOP (L31), never as a stop of their own.

`check` must pass before the Stage 2 "next" is recorded. `course_gate.py` says an incomplete map loud on every module
start and never stops on it.
