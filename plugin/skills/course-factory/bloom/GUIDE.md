# Bloom — what level the course asks for, what level the tasks reach, and how to lift them (L48)

Read this lane when an ILO, a Sub-ILO or a task is written, judged or upgraded — at the Stage 2
architecture, the Stage 3 content script, and in RETROFIT when an old course is assessed.
The data is `knowledge/bloom.json`; the report is `scripts/bloom_map.py`. This file is the judgement
the lists cannot make. In 2.25.0 every Bloom finding is a **suggestion** — shown, never blocking.

**Why (owner, 2026-10-15):** on paper and in Google Classroom the tasks were almost all *Remember*.
The tablet lets a trainee operate, find and decide. The factory's job is to use that — to lift the
level of the tasks up to what the ILOs ask, and above *Remember* wherever the content allows.

## 1 · The six levels, in one line each

| | Level | The trainee can … | Tablet task types that reach it |
|---|---|---|---|
| 1 | Remember | recall a fact, a name, a number | choose one, label, tap the part |
| 2 | Understand | explain, sort, compare | match, sort into groups, order |
| 3 | Apply | operate, set, measure, carry out | operate the panel, set the value, read the instrument |
| 4 | Analyse | find the cause, the fault, the hazard | **find the fault**, find the hazards, **rebuild the incident**, a scenario |
| 5 | Evaluate | decide and say why; judge a decision | choose-and-justify, **spot the errors** in a filled-in document, **compare** the options, **build the plan** |
| 6 | Create | make a plan, a procedure, a checklist | only **build the plan**, written for the situation, comes near; real creation is the practical exercise |

## 2 · Judging what the list cannot

- **The ILO's level is its highest leading verb.** "Identify the tank types and describe their
  construction" is *Understand* (describe), not *Remember*. `bloom_map.py` reads it that way.
- **A verb that is not in the list** (select, determine, check, ensure, определить …) depends on the
  sentence. Decide from what the trainee would be *seen doing*: "select the extinguishing agent for a
  class B fire" is *Apply*; "select the safer of two loading plans" is *Evaluate*. Write the level into
  `architecture.json` on the Sub-ILO: `"bloom": 3`. Never guess silently.
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

## 3 · Lifting a task — the tablet patterns

Lift one level at a time, to the Sub-ILO's level and no further without a reason on board (section 5); what the outcome
asks to know by heart keeps its recall question.

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
estimated); the module's share at *Apply* or higher (suggested at least 50 %); every task below its
Sub-ILO; and for each, the tablet task types that would lift it. The same section is on the Stage 2
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

**Proposed - keep or lift, decided topic by topic.** Lifting the Bloom level is the aim of this step: every topic the
old course teaches below its outcome is lifted unless something real stops it. The target is the level the outcome
asks for - not the highest level there is; raising numbers is not the goal, teaching what the job needs is.

- **Keep** only with a reason. When the old course already reaches what the outcome asks, the documents say so
  themselves ("Kept because the old course already reaches ...") - lifting further would be overdoing it. When a topic
  stays **below** its outcome - kept or lifted only part of the way - `limit` says what stops this course reaching it:
  no simulator for it, no equipment, no time in the programme's hours. Without `limit` the check refuses it. `how` still says what gets better at that level
  (a photograph instead of a slide of text, the recall moved into the self-check), or "kept as it is".
- **Lift** when the old course falls short: up to the outcome's level - one step is often enough, the next course can
  take the next - or as high as this course can honestly reach on its tablets, simulators and equipment, with `why`
  saying what stops it. A lift never removes the recall: what must be known by heart is still asked as a recall
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
`how`. Tell the operator where the documents are and that the experts sign the Word files.
