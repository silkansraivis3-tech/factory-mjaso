# Orchestration — one agent reads the programme, then the modules are built at once

Read this when a **whole course** is being built from a knowledge base, and the module count is
large enough that building them one after another is the slow part.

**The short answer to "is it possible": yes, and it is not the hard part.** Eight modules built by
eight agents in parallel is a normal fan-out. The hard part is everything that must be decided
*before* the fan-out, because eight agents cannot negotiate with each other — and the reason this
guide exists is that the failures are all in that seam, not in the parallelism.

---

## The shape

```
  0  READER          one agent, alone with the knowledge base
     |               programme · model course · what each module teaches
     |               writes:  MODULE_MAP.md   ILO_MAP.md   (files, never slides)
     v
  =  GATE            the owner approves the table. Nothing is built until they do.
     |
     v
  1..N MODULE        one agent per module, all at once
     |               each owns exactly one folder and nothing else
     v
  Q  QA              per module as it lands, then one cross-module pass
     |
     v
  +  ASSEMBLY        the orchestrator alone: registry, handout, hours total, publish
```

Four rules hold that shape together. Each is here because dropping it produces a specific,
recognisable wreck.

---

## Rule 1 · Everything shared is decided before the fan-out

A parallel agent cannot ask another agent a question. So anything two modules could disagree about
has to be settled by the reader and frozen at the gate:

| Settled before fan-out | Why, in one line |
|---|---|
| **The minutes per module** | Two agents both "rounding up to fit" is how a course built to 2175 minutes against an accredited 1640. L1. |
| **The module split and numbering** | A module that renumbers itself breaks every cross-reference in every other module. |
| **COURSE_LANGUAGE** | L6. One agent quietly translating is the drift this factory already has a check for. |
| **The visual system** | L12 and the token set. Eight agents inventing eight dialects is exactly what `audit_ui.py --strict` exists to stop. |
| **Task code ranges** | Module 3 owning `GAS3xx` and nobody else touching it. |
| **The ILO map** | Below. This is the one that actually makes parallelism work. |

> If something is not on that list and two modules could still collide over it, it belongs on that
> list. Add it before the run, not after the merge.

---

## Rule 2 · The reader's output is a FILE, and it is not slides

The first agent works alone with the programme, the model course and the knowledge base, and
produces two documents in the course folder:

**`MODULE_MAP.md`** — module → official topic numbers → allocated minutes (theory / practical) →
what the module teaches → what it checks → whether it needs a facility. The minutes column sums to
the programme total or the reader has not finished.

**`ILO_MAP.md`** — for every module: which Main ILO and which Sub-ILOs are taught there, **and how**
— taught, practised, or assessed, against which screen, task or practical. One row per outcome.

> **The ILO map never appears in a slide.** It is the build's own instrument: it tells each module
> agent what it owes, and it tells the QA agent what to check. A trainee does not need to read a
> traceability matrix, and putting one on a screen is how a course starts looking like a compliance
> document instead of teaching material — see L22.

Two further reasons the map is a file and not a conversation. A file is the only thing eight agents
can all read without eight copies of the knowledge base going into eight contexts. And a file is
what the owner actually reviews at the gate — a table they can disagree with line by line, while
disagreeing is still free.

---

## Rule 3 · One agent, one folder — and the orchestrator owns everything shared

Every module agent may write **only** inside `modules/mN/`. Everything that more than one module
touches is written by the orchestrator after the fan-out, alone:

- `courses/<id>/course.json` and the generated `courses/registry.js`
- the handout — it is one document with one running structure, and it is also the overflow valve
  for L1, so it cannot be assembled until every module knows what it could not fit
- the instructor run content, the task manifest, the cross-module checks
- anything under the terminals

This is not tidiness. Two agents writing the same file is a lost write that no test catches,
because the file is still valid HTML afterwards — it is just missing one agent's work.

---

## Rule 4 · QA runs per module, then once across all of them

"One extra agent that checks if all modules are being created well" is right, with one correction
worth making: a QA agent has nothing to check while a module is still being written. So run it as a
**pipeline**, not as a ninth parallel worker —

- **as each module lands**, a QA agent reads that module against its rows in `ILO_MAP.md` and its
  minutes in `MODULE_MAP.md`, and runs the deterministic checks. Module 3 is being verified while
  Module 7 is still being written; no wall-clock is wasted.
- **once at the end**, a single cross-module pass that only it can do: task codes unique across the
  course, terminology consistent, the hours total, the visual dialect, every cross-reference
  between modules resolving, every outcome in the ILO map taught somewhere.

The per-module QA agent must be a **different** agent from the one that built the module. An agent
asked to check its own work confirms it.

---

## What the agents are

| | Model | Tools | Reads | Writes |
|---|---|---|---|---|
| **Reader** | the strongest available | read + search only | programme, model course, KB | `MODULE_MAP.md`, `ILO_MAP.md` |
| **Module** | the strongest available | full | its own rows of the two maps, the visual system, its source extracts | `modules/mN/` only |
| **Visual** | one that can generate — `model: "fable"` | read, write, web | a `GENERATED_ASSET_REQUIRED` brief | the asset files named in the brief |
| **QA** | strong; never the builder | read + run checks | the module, the two maps | a findings list — **never a fix** |

**The visual agent is how the model switch happens automatically.** The `Agent` tool takes a `model`
override, so when a module reaches an image this model cannot produce, the factory does not stop and
does not ask the owner to change models by hand — it spawns that one piece of work on a model that
can, and carries on. `course-visuals/scripts/write_visual_handoff.py` writes the same request to a
file as the fallback, for the case where no override is available. Build the module as far as it
goes either way; never leave it unfinished because one picture is missing.

---

## Is it hard?

Honestly: **the fan-out is easy and the seams are not.** Writing eight agents takes one call. What
takes the care is the six rows of the table in Rule 1, the two map files, and the discipline that
one agent writes one folder. Every one of those exists because of a failure this factory already
recorded — hours that did not add up, a course that changed language one screen at a time, a second
visual dialect, a section nothing linked to.

Two things that are genuinely harder than they look, and are worth knowing before starting:

- **Cost is not divided, it is multiplied.** Eight agents building eight modules is eight modules'
  worth of work happening at once, not one module's worth spread thinner. Parallelism buys
  wall-clock, never tokens.
- **A failed agent must not silently produce a thin module.** An agent that could not find its
  source material will still return something. That is what the per-module QA pass and
  `classify_module.py` are for: a module that classifies C after a full build did not finish, and
  the run must say so rather than reporting eight successes.

---

## Running it

`orchestration/workflows/build_course.js` is a ready script for the `Workflow` tool: reader → gate →
parallel modules with QA pipelined behind each → the cross-module pass. Read it before running it —
it is deliberately short, and the module prompt inside it is the thing worth editing for a
particular course.

**The gate is not automated, and must not be.** The script stops after the reader and prints the
table. The module split and the minutes are the expensive things to get wrong, and changing a table
row is free while changing eight built modules is not.
