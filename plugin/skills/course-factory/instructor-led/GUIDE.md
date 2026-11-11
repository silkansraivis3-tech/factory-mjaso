# The Instructor-Led Course Development Guideline - what the course owes it (L68)

Read §0 before a module's content script is written, and the rest after a module's exercises are written (the Trainee
and Instructor forms in `to_review\exercises\`) and before the course is handed over. The rules, limits, TLA pool and review checklist are `knowledge/instructor-led.json`;
the check is `scripts/instructor_led.py`; the module plan shows the result (`compile/scripts/module_plan.py`) and the
additional materials print the paper (`compile/scripts/additional_materials.py`).

The guideline adds no parallel set of documents. It sets what the factory's outputs must contain, and adds four paper
items: the pre-brief card, the debrief card, the observation card and the employer sheet. Main ILOs, hours and facts are
never changed by it (L1, L2, L4).

## 0 · Choose the formats while the module is written (2.128.0)

Aigars Kluga (2026-11-11): *"the factory is good but cannot vary - fine for one-direction courses like Gas, but narrow."*
The guideline chooses in this order: task type → method → cheapest modality that gives the right cues → Bloom tag. So
before a module's content script is drafted:

```
python scripts/instructor_led.py plan <course> --module 3
```

reads the module's Sub-ILOs from the ILO map and, for each, prints its task type - the register's, or read from its verb
(`knowledge/instructor-led.json` `"formats"` `"verbs"`: the earliest verb decides; none is a decision) - and one or two TLAs
near its Bloom level, varied across the module (`scripts/activity_formats.py`), each with how it is written in the script.
A decision gets a case dilemma, a refutation card, a contrast pair, a worked example ...; a real-time outcome the scenario
run with two to four planned events; a hands-on outcome the demonstration (Peyton four-step) or a planted-defect
inspection; a team outcome a closed-loop or challenge-and-response drill with another team observing and a trainee-led
debrief. The register gets the task type (`"_task_type_from"` says where it came from) and the TLA names where it has none -
a draft; the operator confirms the task type (R2).

Then write the module in those formats. An activity screen names its format - `"format": "scenario-run"` (the keys are
`"formats"` `"pool"`) - and may carry the words its practical's cards are drafted from, approved with the script:
`"objective"`, `"roles"`, `"safety"` (lines; required in the script for a simulator or real equipment - never drafted),
`"observe"` (2-3 lines), `"events"` (a scenario run's planned events), `"team"`. The script check makes a module a
**must-fix** when it came out one direction anyway (`content_script.py` `a_one_direction`: two or more activity screens all
one format, or three or more practice moments - activity screens and active slides - all one format), or when a team,
real-time or hands-on Sub-ILO has no activity of its kind (`a_type_unserved`). `"formats_why"` at the top of the script
keeps both a note.

## 1 · Write the course's file

```
python scripts/instructor_led.py draft <course>
```

writes `working_claude\instructor_led.json`, or adds what it lacks, from the approved scripts and the ILO map, and keeps
everything already filled: a row per Sub-ILO with its task type, its TLAs (the formats the script used, else the plan's)
and its evidence (the activities, committing slides and tablet sets that name it; the final's questions that do); and a
practical for every simulator and real-equipment exercise and every room drill, team scenario and project block (2.128.0,
the format's `"practical"` - a case, a map or a discussion needs none), with cycle rows that add up to the screen's minutes
and the cards' fields from the screen's own words or the format's catalogue entry. What the material does not give - the
must-know facts, a simulator's or equipment's safety, a recorded run and its form, the employer sheet - is left empty, and
draft lists the safety lines still to fill. Check every drafted value with the operator at the next STOP (L31); none is
invented (L4).

**`register`** - one row per Sub-ILO, the outcome register's added columns (guideline 5.1):

- `task_type` - the dominant task type: `fixed_sequence`, `decision`, `real_time_judgement` or `team_behaviour` (R2). It
  picks the TLA. A blended exercise stays whole.
- `must_know` - the few facts kept in the head: when it matters on board, there is no aid at hand or no time to use it
  (R3). An empty list is a fine answer.
- `lookup` - every other fact the exercise uses, with the aid it is practised with: `{"fact": ..., "aid": "the SDS"}`.
- `evidence` - `{"practice": [...], "scored": [...]}`: how we will see it, inside the hours, with our equipment.
- `criteria` - what the exercise must show; `"must_pass": true` where a miss is unsafe, with `"step": "M05.A01 4"` - the
  recorded run's form step that carries it, so a strong run cannot hide it.
- `tla` - the TLA names from the pool (`knowledge/instructor-led.json` `tla_pool`), as they go into the method column.

A Sub-ILO whose verb cannot be watched ("understand", "be familiar with") is re-expressed through the ILO map with the
operator's yes (L2, `bloom.json` `weak`) - the check names it, this file does not change it.

**`practicals`** - keyed `"M04.A01"` (the module and the activity screen's id). Every simulator and real-equipment exercise
has one; a classroom exercise only when it is a drill, a role-play, a team scenario or a project block (draft makes these
from the activity's `"format"`). A tablet task, a case, a map or a discussion needs none.

- `cycle` - the rows inside the exercise's own minutes, in order: `brief` (3-5 min), `show` (first exposure only) or
  `diagnostic` (an experienced group: each trainee tries unassisted first), `run` (as many as there are), `debrief`
  (15-20 min for a team drill or simulator run, 5-10 alone). `{"kind": "run", "min": 20, "what": "Peyton steps 3-4"}` -
  `what` shows in the plan's instructor column. The rows add up to the screen's minutes exactly: brief and debrief come
  out of the exercise's time, never on top of it (L1).
- `team` - true for a team drill or simulator run (the longer debrief).
- `practice_runs` - runs each trainee completes; at least two after the first correct one (R9).
- `prebrief` - `objective` (one sentence: what you will be able to do at the end), `roles` (who performs, who observes,
  who plays outside roles), `safety` (the hazards and limits, a list), `stop_word`, and `intervention` only when it differs
  from "I will watch and stay quiet ..." (R10: stop-and-go coaching on a novice's first runs of a drill is allowed - say so).
- `debrief` - `must_observe` (two or three steps or behaviours this run exists for), `prompt_1`, `prompt_2` when the run has
  its own (the defaults are the guideline's), `reactions` and `close` likewise. `observe` - the observation card's lines,
  when they differ from `must_observe`.
- A recorded run is its own practical, later than its practice - the next module or the next day: `"recorded": true`,
  `practice_of` (the practice's key), `changed_condition` (one planted condition, drawn from a fixed list), and `form` -
  `critical`: 8-12 `{"step": ..., "stop": true|false}`, the stop criteria among them ("recognises when to stop"). `gwo`:
  true adds the GWO 0-3 line.

**`must_pass`** - the final's 6-8 must-pass question ids (its script's screen ids). Marked here; the training app does not
yet fail a candidate on one of them - say so to the operator, do not promise it.

**`employer`** - one sheet per course (guideline 5.6): `can_do` (3-5 sub-outcomes in behaviour the company can observe),
`decays` (the sequences and numbers that decay fastest - the honest figure is added), `drill` (one 15-minute on-board drill
at 1-3 months an officer can run), `watch_for` (2-3 behaviours on board that show the training held), `refresher` (what
the regulation does and does not require). Behaviour change, never accident reduction.

**`justify`** - `{"M02": {"C10": "Novices meeting the gas laws for the first time"}}`: one line for a checklist item the
module cannot meet, keyed by the item or its rule (`"R6"`). Novices meeting a concept for the first time and
second-language groups are valid reasons for passive theory; the reviewer may reject any line.

## 2 · Check, then the operator's yes

```
python scripts/instructor_led.py check <course> [--module 4] [--json]
```

goes through the guideline's review checklist (section 7): **yes**, **NO** (with what to fix), **JUSTIFIED** (with its
line - never counted as passed), **n/a** (nothing in the module to judge - never counted as passed either), **elsewhere** (checked by another part of the factory, named) and **by hand** (what only
a reviewer can judge: a sea story, a decorative photograph, written English in a scored item, three surface variants).
Exit 1 while any item is NO. Fix in the content script (`content_script.py propose`, L29) what is the script's - an active
slide's notes that only ask the room, a passive block longer than 15 minutes - and in this file what is this file's.

Show the operator the file in plain words - the cycles, the cards, the must-pass questions, the employer sheet, every
justification - and on their yes:

```
python scripts/instructor_led.py approve <course> --by "<the operator's name>"
```

Any change afterwards makes it unapproved again (`status` says so), and the practical kit waits for a new yes.

## 3 · What the factory then makes

- **The module plan** (`instructor\M01_PLAN.html`): the passive share of the theory minutes and the longest passive run on
  its face, with the justification or a warning when it is over 20 %; an active slide whose notes name no output for every
  trainee marked "counted passive"; each exercise's brief / show / run / debrief rows inside its minutes; the outcome
  register's task type, must-know and evidence beside every Sub-ILO.
- **The practical kit** (`course\additional-materials\practical-kit\`, by day): the pre-brief card and the debrief card
  with the observation card for every practical, the assessment form for every recorded run, the employer sheet - Word and
  PDF, linked from `INDEX.html`. Only from an approved file.

## 4 · Not the factory's yet

- The final test on the trainees' phones, and filling the assessment form on the instructor's tablet: the training app's.
  The factory writes each recorded-run assessment form as `modules\classroom\forms\<CODE>.json` (`classroom_files.py`), which
  the app imports.
- A must-pass question failing a candidate: the final's marking is the app's.
- "No decorative photos": against L52 (as many real photographs as possible) - a decision for the owner, until then a
  by-hand item.
- Counting a tablet task as a practical hour (R7): the factory never moves the programme's hours (L1, L49).
