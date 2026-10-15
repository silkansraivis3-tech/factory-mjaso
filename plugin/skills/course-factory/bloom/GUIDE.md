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
| 4 | Analyse | find the cause, the fault, the hazard | find the hazards, a scenario, sort symptoms into causes |
| 5 | Evaluate | decide and say why; judge a decision | choose-and-justify, a scenario with reasons |
| 6 | Create | make a plan, a procedure, a checklist | **no task type yet** — part 3 of the Bloom plan |

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

Lift one level at a time, to the Sub-ILO's level — and above *Remember* wherever the content allows.

| From | To | How, on the tablet |
|---|---|---|
| choose the definition | Apply | **set the value** on a gauge, **operate the panel**, **read the instrument** and act on it |
| tap the part | Apply | **tap where you would act** — the valve to close, the point to measure |
| order the steps (from memory) | Apply | **line up the valves** for the operation, in the order they are done |
| match term to definition | Understand → Analyse | match **each symptom to its cause**; sort symptoms into causes |
| choose the fact | Analyse | **find the hazards** in the scene; a gauge reading that is wrong — what is the fault? |
| choose the action | Evaluate | **choose-and-justify**: the action, then the reason; a **scenario** that shows the consequence |
| — | Evaluate | **judge a decision**: a colleague's filled-in permit or plan with a mistake — find it and say why |

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
