# Bloom — what level the course asks for, what level the tasks reach, and how to lift them (L48)

Read this lane when an ILO, a Sub-ILO or a task is written, judged or upgraded — at the Stage 2
architecture, the Stage 3 content script, and in RETROFIT when an old course is assessed.
The data is `knowledge/bloom.json`; the report is `scripts/bloom_map.py`. This file is the judgement
the lists cannot make. The Bloom card on the review pages is a **suggestion** — shown, never blocking; the experts'
documents (§5) are a gate.

**Why (owner, 2026-10-15):** on paper and in Google Classroom the tasks were almost all *Remember*.
The tablet lets a trainee operate, find and decide. The factory's job is to use that — to lift the
level of the **tasks** up to what the ILOs ask. Never the outcome: the job sets the level, and a higher
level is not a better outcome.

**The seven rules (pedagogy lead, Instructor-Led Course Design Framework, 2 Nov 2026 — `bloom.json` `"rules"`):**

| | Rule | In the factory |
|---|---|---|
| B1 | Tag every outcome with one level | `bloom_map.py` reads every ILO and Sub-ILO; one it cannot read is said |
| B2 | Never raise a regulator's outcome by rewording it; add a sub-outcome beside it | L2, guideline R1 |
| B3 | The job sets the level. A must-know rule stays at *Remember*, however critical | §5: *Remember is a right answer* |
| B4 | Check for tags that are too low: "knows" or "describes" where the job is a decision | `instructor_led.py check`, asked under C5 |
| B5 | The trainee practises at the tagged level at least once, and is assessed at it | the module map: a question below its Sub-ILO, a Sub-ILO the module check or the practice does not reach |
| B6 | Lower levels are prerequisites, not separate lessons; do not walk every topic up all six | §3: a lift never removes the recall |
| B7 | No quota: no target share of higher-level outcomes | the 50 % in §4 counts **questions**, and is a suggestion |

Bloom is a tag. It does not choose the method — the task type does (`instructor-led/GUIDE.md` §0) — because it
describes thinking and says nothing about what the hands must learn or how people behave towards each other.

## 1 · The six levels, in one line each

| | Level | The trainee can … | Tablet task types that reach it |
|---|---|---|---|
| 1 | Remember | recall a fact, a name, a number | choose one, label, tap the part |
| 2 | Understand | give the reason or the meaning in their own words | match, sort into groups, order |
| 3 | Apply | use a rule, a procedure or an aid: operate, set, measure, carry out | operate the panel, set the value, read the instrument |
| 4 | Analyse | find what matters or what is wrong: the cause, the fault, the hazard; compare | **find the fault**, find the hazards, **rebuild the incident**, a scenario |
| 5 | Evaluate | decide and say why; judge a decision | choose-and-justify, **spot the errors** in a filled-in document, **compare** the options, **build the plan** |
| 6 | Create | make a plan, a procedure, a checklist | only **build the plan**, written for the situation, comes near; real creation is the practical exercise |

## 2 · Judging what the list cannot

- **The ILO's level is its highest leading verb.** "Identify the tank types and describe their
  construction" is *Understand* (describe), not *Remember*. `bloom_map.py` reads it that way.
- **A verb that is not in the list** (select, determine, check, ensure, определить …) depends on the
  sentence. Decide from what the trainee would be *seen doing*: "select the extinguishing agent for a
  class B fire" is *Apply*; "select the safer of two loading plans" is *Evaluate*. Write the level into
  `architecture.json` on the Sub-ILO: `"bloom": 3`. Never guess silently. For *select*, *check* and *prepare*
  the Stage 2 page shows the question that tells the two levels apart (§2a).
- **A verb of the hands or of the team** (dons, rigs, launches; orders, holds, aborts; briefs, calls out,
  challenges) has **no Bloom level**: Bloom covers thinking only. The Stage 2 page says so instead of
  "could not be read". Give a level only to the thinking inside it - the go or no-go decision inside a
  drill - with `"bloom": n`; never force one onto the physical or behavioural part. Name the standard
  instead: time, sequence, tolerance or must-pass step.
- **A question can sit higher than its task type usually does.** A "choose one" built on a real
  situation, where the answer must be worked out, is *Analyse*. Then give the question
  `"bloom": 4, "bloom_why": "<what the trainee has to work out>"`. Say it only when it is true — the
  operator reads it.
- **Difficulty is not level.** An obscure number is still *Remember*. A trick option is still
  *Remember*. A higher level means a different kind of thinking, not a harder fact.
- **Weak verbs** (know, understand, be aware, zināt, saprast, знать, понимать) cannot be watched. A
  programme's **Main ILO stays verbatim (L2)** — the report only notes it. A **Sub-ILO** may be
  re-expressed with a verb that can be watched (status `re-expressed`, with `why`) — the operator
  approves it at the Stage 2 STOP. Choose the verb the programme's intent supports, never a higher
  one just to look better.

## 2a · Choosing the verb of an outcome we write (2.141.0)

The pedagogy lead's Bloom Verb Guide for Course Developers (23 Nov 2026) - `bloom.json` `"verb_guide"` and the
`write` / `use_when` / `assess_with` fields of each level. It is for the outcomes **we** write: a Sub-ILO added or
re-expressed beside a regulator's outcome, or an in-house outcome. **A regulator's wording is never changed.**

**Choose the verb last.** (1) Name the job task in one line. (2) Set the level from that task. (3) Take the plainest
verb in that level's row. (4) Finish the sentence: verb + object + condition + standard. (5) Test it: would two
assessors agree, and does the assessment item ask for the same verb? If no verb in the row fits, the level is
probably wrong - go back to step 2.

| Level | Use when the job task is | Verbs to write with | Assess with |
|---|---|---|---|
| Remember | recalling a fact, limit, signal or step with no aid | state, list, name, label, recognise | short recall item, oral question |
| Understand | giving the reason or the meaning in their own words | explain, describe, summarise, give an example of, classify | "explain why" question, teach-back |
| Apply | using a rule, procedure or aid in a routine case | use, carry out, complete, calculate, operate, read, select | worked task with the aid in hand |
| Analyse | finding what matters or what is wrong | compare, distinguish, diagnose, trace, sort, find the cause of | scenario item with data to interpret |
| Evaluate | judging against criteria and committing to a decision | decide, judge, justify, prioritise, accept, refuse, recommend | scenario decision with justification, oral probe |
| Create | producing a new plan or document | plan, draft, design, prepare, propose | product scored against a checklist |

- **One verb per outcome.** "List and explain" is two outcomes, or one tagged at the higher level - which is how
  `bloom_map.py` reads it.
- **Plain verb over impressive verb.** English is a second language for most trainees and many instructors.
- **Change the verb and as few other words as possible.** The topic and the scope stay as they were.
- **Third person, present tense:** "States", "Uses", "Decides".
- **Verbs that change level with the task** - identify, explain, describe, select, check, calculate. The *condition*
  fixes the level, so always write it: "from a given list", "with the SDS in hand", "in an unfamiliar scenario". The
  question that tells the two apart is in `"depends"` ("Was the answer taught as a fact, or must it be worked out?").
- **Verbs to avoid** (`"avoid"`): understand, know, be aware of, be familiar with, demonstrate knowledge of, discuss,
  participate in, attend, learn, study, review, and the hard words (elucidate, ascertain, appraise, synthesise,
  formulate). Each hides a real verb - ask "what would the trainee do to show this?" and write that. **Replace rather
  than tag:** *demonstrate* (name what the assessor sees: dons, launches, completes) and *assess* (judge or decide).
  A Sub-ILO that opens with one gets a note on the Stage 2 page, with what to write instead. On the Bloom card it is
  a note, never a stop. In an instructor-led course the ones no assessor can see (`"observable": false` - all but the
  hard words, *demonstrate* and *assess*) fail checklist item C2 exactly as *know* and *understand* always did: the
  Sub-ILO is re-expressed, or the module justifies it in one line.
- **`prepare` is asked, like select and check.** The guide writes it at Create (a plan, a document); programmes also
  use it for making equipment ready by a procedure (Apply). The Stage 2 page asks which, and the level is written on
  the Sub-ILO.

## 3 · Lifting a task — the tablet patterns

Lift one level a course - Remember to Understand, Understand to Apply - and never past the Sub-ILO's level without a
reason on board (section 5); more than one level only when the expert decides it. What the outcome asks to know by heart
keeps its recall question.

| From | To | How, on the tablet |
|---|---|---|
| choose the definition | Apply | **set the value** on a gauge, **operate the panel**, **read the instrument** and act on it |
| tap the part | Apply | **tap where you would act** — the valve to close, the point to measure |
| order the steps (from memory) | Apply | **line up the valves** for the operation, in the order they are done |
| match term to definition | Understand → Analyse | match **each symptom to its cause**; sort symptoms into causes |
| choose the fact | Analyse | **find the hazards** in the scene; a gauge reading that is wrong — what is the fault? |
| choose the action | Evaluate | **choose-and-justify**: the action, then the reason; a **scenario** that shows the consequence |
| — | Evaluate | **spot the errors**: a colleague's filled-in permit or plan — tap every wrong line, see why |
| choose the cause | Analyse | **find the fault**: symptoms first, then check the parts one by one, then name the fault |
| order the steps | Evaluate | **build the plan** from cards, some of which do not belong; **rebuild the incident** and tap where it should have stopped |
| choose the fact | Evaluate | **compare** two plans or readings side by side with real figures, and choose the safer |

Every lifted task still obeys the rest: the answer is taught on the slides before it (L36), the
tablet rules (L42), the variety floors (L38), a real picture for real equipment (L33).

## 4 · The report

```
python scripts/bloom_map.py --course <course>              # the whole course, from architecture.json
python scripts/bloom_map.py --course <course> --module 1   # one module, from its content script
```

It prints, in the operator's language: the level of every ILO; the level each task reaches (stated or
estimated); the module's share of **questions** at *Apply* or higher (suggested at least 50 % — never a
share of outcomes, and a module of must-know facts may sit below it); every task below its
Sub-ILO; every Sub-ILO that no practice moment reaches before it is checked (a self-check question, or an
activity or active slide by its format's Bloom tag — rule B5); and for each, the tablet task types that would lift it. The same section is on the Stage 2
architecture page and on each Stage 3 review page. To link a question to the Sub-ILO it checks, give it
`"sub_ilo": "1.1"` in the content script — then the gaps are shown per Sub-ILO, not only per module.

Tell the operator plainly (L25): where the course is now ("most questions are Remember"), where it
can go ("the module check could have the trainee line up the valves — Apply"), and what it needs from
them (approve a re-expressed Sub-ILO, or a picture of the panel).

## 5 · The experts' documents — the first thing a course gives its experts

Before any content script is written, the course experts get three documents, topic by topic and module by module:
**Bloom now** (the old course), **Bloom proposed** (the new course) and **Teaching and learning activities**. They are
written at Stage 2, once the architecture has its Sub-ILOs and its `active_learning` proposals, and the Stage 2 page
cannot be approved without them (`make_architecture_page.py --approve`).

```
python scripts/pedagogy_review.py draft  --course <course>    # one empty row per topic, in working_claude/pedagogy_review.json
python scripts/pedagogy_review.py check  --course <course>    # what is missing; exit 2 until it is clean
python scripts/pedagogy_review.py render --course <course>    # to_review\pedagogy\: 1_BLOOM_NOW, 2_BLOOM_PROPOSED,
                                                              # 3_TEACHING_ACTIVITIES - each .docx, .html and .pdf
```

The outcomes' words are read from the architecture, never written in this file: the documents cannot change one.

**Now - what the old course really made the trainee do.** For each topic, read its deck, exercises and tests
(`OLD_COURSE_INVENTORY.md`, the old course's own files). The level is the highest one the old course *both* taught and
asked the trainee to do - slides read out and a recall question are Remember, however hard the fact; a paper exercise
that calculates or carries out the procedure is Apply; a simulator run judged by its result is Apply or Analyse.
`how` says how it was taught, `checked` which test question or exercise checked it ("not checked" when none did),
`where` the file and slides ("Topic 4 deck S3-S20; final test 02C-1 Q12-14"). A topic the old course never taught is
level 0, with `how` saying so.

**Proposed - raise or keep, one outcome at a time (2.142.0).** The pedagogy lead's ILO elevation method
(`knowledge/ilo-elevation.json`, `scripts/ilo_elevation.py`); the reference result is his spreadsheet for IMO 1.04
(296 outcomes: 84 % Remember before, 20 % Remember or Understand after). Judged as a whole course, outcomes get
grouped, half are quietly left where they are, the same activity comes back everywhere and a raised outcome is
re-written from scratch. So the code counts, loops and checks, and you give **one small answer about one outcome**:

```
python scripts/pedagogy_review.py next    --course <course>   # the ONE outcome to decide - later, the ONE task to propose
python scripts/pedagogy_review.py propose --course <course> --module 4 --topic 4.1 --decision raise --level 4 \
        --text "<the re-worded outcome>" --does "<what the learner does at that level>" --why "<why, for this outcome>"
python scripts/pedagogy_review.py propose --course <course> --module 4 --topic 4.2 --decision keep --codes PRE,CNF --why "<why>"
python scripts/pedagogy_review.py task    --course <course> --module 4 --topic 4.1 --tla key-feature --how "<the task>" --fit strong
python scripts/pedagogy_review.py status  --course <course>   # decided n / total, raised and kept, each keep code, each TLA
```

Run `next`, answer that outcome only, run `next` again - never judge two at once, never write a decision into the
file by hand. An answer that fails a check is **not saved** and the check is named: answer that outcome once more for
that check. All outcomes first, then the tasks in syllabus order.

- **Raise is the default.** A raise lands on Apply, Analyse, Evaluate or Create - the level the content *naturally
  supports*, not the highest you can argue for. Remember to Understand is not a raise. A level is never lowered.
- **The honesty test (`--does`).** One sentence: what the learner would actually do with this content at the new
  level, on board or in training. If you can only write it by adding content the outcome does not contain, **keep**.
- **Where a raise usually lands.** These are novices on a basic course: Apply and Analyse are the usual landing.
  Evaluate needs a criterion to judge against that is *in the content*; Create only when the content is about
  producing a plan, a checklist, a procedure or a drill. A small fact still gets a modest application - use it, find
  it, check a case against it. A fact the trainee may look up (where something is listed) is raised to *using that
  reference*, not kept.
- **What is kept, on purpose - a minority.** The basic set of types or definitions that later outcomes stand on (PRE)
  or that are easily mixed up (CNF); a safety fact, or an immediate action ("when X happens, do Y"), recalled at once
  with no aid (SAF, REC). THN is the last resort, for an outcome with nothing in it to use, compare or judge.
- **Keep only with a code and a reason about this outcome.** At Remember or Understand: PRE prerequisite for a
  higher-level outcome, SAF safety-critical fact, REC recalled without lookup, CNF easily confused, FRQ used
  repeatedly inside larger tasks, LOD looking it up would overload a time-pressured task, THN too thin to raise
  honestly. At Apply or above: ALR already there and no higher level fits. Do not keep because raising takes effort,
  and do not raise just to raise - both are failures, and `status` shows the kept share and each code's count.
- **The rewrite is the verb and a minimal fit (`--text`).** Start with ONE verb of the level's list, third person
  (`next` prints them - they are the Bloom Verb Guide's, §2a). Keep the technical content in the original words; change
  only the grammar the new verb needs. Add nothing - no fact, number, equipment, document, regulation, condition or
  task. Remove nothing - every item of a list stays. A kept outcome is not re-typed: the original is shown as it is.
  *States that a cargo tank is entered only when the oxygen reading is 21 % ...* becomes *Verifies that a cargo tank is
  entered only when the oxygen reading is 21 % ...* - never *Verifies the entry conditions and completes a permit*.
- **The task (`task`).** One TLA of the pool at the outcome's final level - `next` lists the only ones the code allows
  there (not the TLA of either of the two outcomes before; none above 15 % of the course once 20 have tasks) - and one
  or two sentences, under 60 words, that name *this* outcome's equipment, values, procedure or situation. A task that
  could be pasted under another outcome is too generic. Fit: `strong` (a TLA of the outcome's own task type, used as
  designed), `adapted` (another task type, or on plans / a simulator / a mock-up - `--fit-note` says what it needs),
  `gap` (a hands-on skill an instructor must watch - an instructor checklist is assumed).
- **When a wording check cannot pass and the raise is honest** (the programme's own number is out of date, the original
  is three words long): `--attention "<why>"` saves the row **flagged** - the expert sees it first - instead of stopping.
- **The expert decides.** The original wording is always beside the proposed one. Take proposed ratifies the raise into
  the architecture as re-expressed, with its level written on the Sub-ILO; an expert's own wording or level is carried
  out as it is, and the checks only warn. A Main ILO is never re-worded (L2): its raise is the level and the task.
- **"Accept the outcome, fix only the task" (2.142.1).** In the editor the expert may take the outcome and its level
  and write the task themselves (an OK whose note starts `Task: `). `pull` puts their words in as the row's task at
  once, by name; nothing is left for the factory to do, and the task's checks only warn.
- **After any change to this method** (this section, `ilo-elevation.json`): run the golden set -
  `pedagogy_review.py golden --set <golden_set.json> --packet <ref>` asks one outcome, `--answers <file>` scores the
  26 answers against the reference (at least 21 decisions, no failed check). The set holds IMO text and is not in the
  repository.

`now` is still judged for every outcome (above): the experts see what the old course did beside the proposal.

**A review started before 2.142.0 - keep or lift, decided topic by topic.** A `pedagogy_review.json` without
`"method": "elevation"` is finished by the rules below, the ones it was started with (`draft --elevation` moves it to
the method above). Lifting the Bloom level is the aim of this step: every topic the
old course teaches below its outcome is lifted unless something real stops it. The target is the level the outcome
asks for - not the highest level there is; raising numbers is not the goal, teaching what the job needs is.

- **Keep** only with a reason. When the old course already reaches what the outcome asks, the documents say so
  themselves ("Kept because the old course already reaches ...") - lifting further would be overdoing it. When a topic
  stays **below** its outcome - kept or lifted only part of the way - `limit` says what stops this course reaching it:
  no simulator for it, no equipment, no time in the programme's hours. Without `limit` the check refuses it - except
  when the topic is lifted its one level and the outcome asks more: the one-level rule is the limit. `how` still says what gets better at that level
  (a photograph instead of a slide of text, the recall moved into the self-check), or "kept as it is".
- **Lift** when the old course falls short: **one level**, toward the outcome's level - the next course takes the next
  (`pedagogy_review.py check` refuses two or more: GAS BASIC lifted 33 topics two or three levels and its theory
  thinned to fit the tasks). Only the expert's decision lifts further. A lift never removes the recall: what must be known by heart is still asked as a recall
  question in the self-check's first part.
- **Above the outcome** only when the work on board needs it and the outcome's verb undersells it - the officer must
  operate what the outcome only asks to describe. Then `above_why` names that task on board. Without it the proposal is
  refused. Never above just to raise the course's numbers.
- **Remember is a right answer.** Limits, definitions, the names of the codes and their chapters, alarm meanings,
  emergency numbers: when the outcome asks for them by heart, they stay at Remember or Understand, taught well.
- **Create (6)** only when the outcome asks for it and a practical exercise produces the plan or the procedure - name
  the exercise. A course whose equipment cannot reach it says so in `why` and stops at Evaluate.
- **Never below the old course.** A level the old course reached is kept.
- **The expert's decision wins.** When an expert says a topic can go higher (or must stay), record it -
  `pedagogy_review.py expert --module 4 --topic 4.1 --level 4 --said "<their words>" --by "<name>"` - and carry it out
  as it is: the rules above no longer apply to that topic; write what the trainee does at that level (`how`, emptied by
  the record) and render again. A Fix with Claude in the editor will record it the same way.

`how` is what the trainee does - the task, the activity, the simulator or equipment exercise - in plain words; `why` is
what it changes for the work on board (shown as "On board"). The documents show each topic's decision (kept, lifted, above the outcome) and
the course's count of each, so the experts see at once where the course changes and where it stays.

**The summaries and the upgrades.** `now_summary` and `proposed_summary`: two or three plain sentences each.
`upgrades`: the course-wide changes in teaching - each `{"what", "why", "modules": "all" or [4, 5]}`, three to seven of
them, the ones an expert would argue about (the self-check's two parts, a simulator exercise for every syllabus gap,
the debrief starting from certain-but-wrong answers, ...).

Plain words for a ship's officer, not for a pedagogue: no level jargon beyond the six names, no technique names in
`how`.

**The experts review them in the editor, not in files.** Once `render` is clean, put the course into the training
app (live, or `--site staging`) and send the documents there:

```
python scripts/course_portal.py create --course <course>             # once: the course in preparation, under intake's course_name
python scripts/course_portal.py link   --course <course> --site staging   # the same course on the other site, if wanted
python scripts/course_portal.py push   --course <course> --pedagogy  # the same words as the Word files, topic by topic
python scripts/course_portal.py pull   --course <course>             # the experts' answers and their Ready
python scripts/course_portal.py status --course <course>
```

Tell the operator the link `push` prints; the office sends it to the experts. In the editor each topic is one card, how
the old course teaches it beside the proposal, and the expert chooses: **Keep as now**, **Take proposed** or **Fix with
Claude** - they say what they want, Claude proposes the level, what the trainee does and why, and they use it or send
only their words as a note. The activities and the upgrades are answered OK or with a note. Then **Ready**, signed with
their name and surname; what they leave unanswered goes ahead as proposed. `pull` carries out a keep (the old course's
level and teaching) and a Claude decision (its level, how and why) as the expert's decision, past every rule above;
writes an OK into the row's `expert_review`, a note into its `expert_notes` (the module's for its own activities, the
whole course's for the summaries and upgrades; `about` says when it is about the activities or upgrades) and
FEEDBACK_LOG.md, and Ready into `ready`. Carry out every note and write in its `done` what was changed -
`check` stops until each one has it, and the editor shows it to the expert - then `render` (it signs the documents
with the Ready) and `push` again: the rows not changed keep their answers.

**The outcomes stay the programme's.** The programme's own words are never lost: a raise is shown beside them and becomes the Sub-ILO only when the expert takes it. In a review started before 2.142.0 the documents never propose a re-worded outcome: `revised_outcome` in a proposal stops `check`, and only an expert who says the outcome should read differently re-words a Sub-ILO - recorded as their decision (`pedagogy_review.py expert`), in English (L19; one in the programme's language stops `check`), its subject and standard unchanged, the programme's own words beside it. A Main ILO is never re-worded (L2). The expert's Take proposed, or a decision with Claude that re-words it, ratifies it into the architecture as re-expressed. After Ready the course is built by L70 (SKILL.md *Auto build*). An expert who cannot use the editor still
gets the Word files and signs them.
