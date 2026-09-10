# Organisation skills — what the factory depends on, and what to do without them

**Owner decision D-3 (2026-09-10):** the `novikontas-*` organisation skills are **not** copied into
this plugin. They reach a machine through a different distribution channel, and a copy would go
stale silently.

So every reference to one is a **conditional** dependency:

1. **Present** → use the organisation skill. It is the authority. Do not second-guess it.
2. **Absent** → use the minimal fallback below. It keeps the factory workflow moving; it does
   **not** pretend to be the organisation skill.
3. **Either way** → record which route was taken in `factory-notes.md` §0.

**How to tell.** Look at the skills available in the session. If the named skill is listed, it is
present. Do not guess from the machine, the folder or a previous run — a colleague's laptop is not
the owner's.

**Never** paraphrase an absent organisation skill from memory and present it as its content. An
absent skill is a stated gap, exactly like an absent source.

---

## Classification

### BLOCKING — a required build step has no other owner

| Org skill | What it owns for us | Build step |
|---|---|---|
| `novikontas-pedagogy-toolkit` | ILO wording, verbs, constructive alignment, assessment design | 4 (co-owner), 12 |
| `novikontas-handouts` | the trainee handout | 11 — and the handout is the hours overflow valve (L1), so this is load-bearing |
| `novikontas-course-start` | the `COURSE_START.json` contract and the honesty-marker definitions | used by all five skills |

### SOFT — a pointer row; the factory completes without it

| Org skill | What it owns | Why the factory still runs |
|---|---|---|
| `novikontas-course-intake` | course type, accreditation, equipment, regulations | `course-factory/SKILL.md` §*The brief* already performs the minimal intake the tablet course needs |
| `novikontas-course-plan` | the course plan document, competence matrix, session plan | a separate human document; nothing on a tablet depends on it |
| `novikontas-brandbook` | logo, corporate colour, typeface, print identity | `course-module-ui/knowledge/tokens.json` already carries the concrete values. Only a **new** brand decision needs the brandbook |
| `novikontas-presentations` | the pptx deck engine, House Rules, copy budgets | this factory ships instructor-led HTML, not pptx |
| `novikontas-course-start-page` | the offline delivery-package start page | the tablet terminals are the delivery target here |
| `novikontas-written-tests`, `novikontas-practical-exercises`, `novikontas-exercise-description-trainee` | Word-format exercise and test artefacts | outside the tablet delivery target |
| `novikontas-skill-conventions`, `novikontas-token-economics` | how a Novikontas skill is authored and costed | maintainer concerns, not part of a course run |

A SOFT dependency that is absent needs **no fallback** — say which skill would have owned the
question, answer it within this factory's own rules, and note it in `factory-notes.md`.

Two more `novikontas-*` strings appear in the bundle and are **not** dependencies:
`novikontas-training-app` in `course-tablet-publisher/knowledge/platform.json` is the GitHub
repository name of the Android platform, and the `novikontas-brandbook` mentions in
`course-task-ux/assets/*.css` are source comments on where a colour came from.

---

## The three fallbacks

Deliberately short. Each is the minimum that keeps the workflow honest, and each says what it is
*not*.

### F/A · Honesty markers — replaces `novikontas-course-start`

Use exactly these four, spelled exactly this way. They already appear in all five skills; this is
the definition, so a session without the organisation skill still has one.

| Marker | Means |
|---|---|
| `UNKNOWN` | Asked, the operator did not know. Record that it was asked. |
| `PLACEHOLDER` | Structure is right, real content is missing. |
| `PROVISIONAL` | Content exists but depends on something unapproved. |
| `[VERIFY: <what to check>]` | Asserted from a source that could not be confirmed. Always carries its payload. |

Every marker written into an artefact must also appear in `factory-notes.md` §6.

**`COURSE_START.json`.** If the contract file does not exist, do **not** invent its schema. Write
the hours block this factory owns (shape in `hours/knowledge/hours-rules.json`) into
`factory-notes.md` §1 instead, and record that `COURSE_START.json` was absent.

**Not provided by this fallback:** traceability tiers, the gap report, persona triage, the redesign
lane, the Word render engine.

### F/B · ILO wording — replaces `novikontas-pedagogy-toolkit`

Enough to keep step 4 moving without inventing pedagogy:

- **Main ILOs are quoted verbatim.** Never rewritten. This is L2 and it is not the toolkit's to
  relax.
- A re-expressed **Sub-ILO** keeps the original beside it, changes the *expression* and never the
  *performance required*, and is marked `PROVISIONAL` until ratified.
- Write an outcome as **verb + object + context + standard**. The verb must be observable —
  *identify, locate, sequence, select, demonstrate, decide, record*. Avoid *understand, know,
  be aware of*: they cannot be assessed.
- **Constructive alignment:** every ILO → the performance required → the teaching activity → the
  practice → the assessment evidence. If an ILO has no assessment evidence, that is a defect, and
  it is the one thing this fallback must still catch.

**Not provided by this fallback:** SOLO depth, Bloom mapping, spaced/interleaved practice design,
assessment validity analysis, the 5–6 ILO cap rationale. If a wording question needs any of those,
mark it `[VERIFY: pedagogy-toolkit absent — <the question>]` and carry on.

### F/C · The handout — replaces `novikontas-handouts`

The handout is required by L1, so it cannot simply be skipped. The minimum that satisfies the
factory:

- One HTML handout, tablet-first, offline, drawing from `course-module-ui`'s token set.
- **Not a copy of the deck.** Do not duplicate its narrative sequence, its instructor framing, its
  activity-launch or answer screens, or its live classroom interactions.
- Three jobs: self-paced learning before or between sessions; reference during class; review before
  the final assessment.
- Carries a table of contents, tap-to-enlarge on every figure, expanders for depth, a terminology
  section, and a self-check.
- **It is the overflow valve.** Every item moved out of class time lands here and is recorded in
  `factory-notes.md` §2 with its source topic.
- Same page contract as everything else on the tablet: a way back, no remote resources, only HTML
  navigation targets.

**Not provided by this fallback:** the organisation's handout house style, its copy budgets, its
Word/print variants, and the slide-image handout format.

---

## Recording the route

`factory-notes.md` §0 carries one row per organisation skill the run touched. A run that records
nothing here is a run that did not check.
