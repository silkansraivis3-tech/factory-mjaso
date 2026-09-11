# Retrofit — the course content exists, the delivery has to be rebuilt

Read this lane when an operator asks for **existing** material to be upgraded, redesigned,
modernised, made presentable, made production-ready, or made like GAS BASIC.

They will not say "retrofit", and they should not have to. `knowledge/routing.json` carries the
triggers; match the **intent**, not the phrase.

---

## The law this lane exists for

> **PRESERVE THE COURSE CONTENT.**
> **DO NOT PRESERVE THE EXISTING DELIVERY IMPLEMENTATION BY DEFAULT.**

The colleague pilot did not fail because the Factory refused to upgrade a module. It failed
because **conservatism looks like diligence.** Keeping an existing layout feels safer than
replacing it, and every individual decision to keep something was defensible. The sum of those
decisions was a module that passed every check and still felt weaker than GAS BASIC.

The existing module is **source material plus learning intent**. It is not the presentation
template, and the fact that its HTML works is not an argument.

`knowledge/content-lock.json` is the authority on which side of the line a thing sits. Read it;
do not re-derive it here. The short form:

| Locked — needs explicit authorisation | Free — redesign on the evidence |
|---|---|
| technical meaning · programme requirements · ILOs · **official hours** · assessment intent · intended practical exercises · course terminology · source-supported facts · **COURSE_LANGUAGE** | screen count · screen order · HTML · layouts · card arrangements · density · progressive disclosure · visual implementation · animation · interactive mechanics · task presentation · navigation · CSS/JS · hierarchy · composition |

---

## Step 1 · Establish the two facts before touching anything

**COURSE_LANGUAGE.** Detect it from the existing course-facing files and the programme, state it
back in one line, and lock it. *The operator's language is not the course's language.* A Latvian
request to redesign an English module produces a Latvian chat report and an English module. Run
`scripts/check_language.py <course> --declare <LANG>` at the end.

**What is authoritative.** The approved programme, the ILO map, the hours. If the existing module
is the only record of them, say so — a retrofit that silently changes hours has changed the
accreditation.

## Step 2 · Classify the delivery: A, B or C

```bash
python retrofit/scripts/classify_module.py <course-or-module>
```

It scores canonical shell, composition vocabulary, teaching visuals, activity screens, tablet
behaviour and token adherence, and returns:

- **A — preserve mostly as-is.** Already on the system and composed.
- **B — moderate delivery redesign.** The system is present but the delivery is thin.
- **C — substantial delivery redesign.** The implementation is not evidence of anything.

**Decide this yourself.** Do not ask the operator to pick a level — they asked for the module to be
made good; choosing how much rebuild that takes is this skill's job. Ask only if the request's
*scope* is genuinely ambiguous.

> **Classify on delivery quality, never on whether the HTML works.** Valid markup, resolving links
> and green checks are not signals and never raise the level. `knowledge/classify.json` lists them
> under `not_signals` precisely so nobody reaches for them.

## Step 3 · Migrate the system — necessary, never sufficient

Route to the owners; the operator never names them.

| | |
|---|---|
| shell, tokens, composition vocabulary, document pages | **`course-module-ui`** |
| screen craft, navigation, the deck engine, measurement | **`course-module-ux`** |
| what representation teaches this, assets, animation law | **`course-visuals`** |
| trainee task screens — only when the module has tasks | **`course-task-ux`** |

A retrofit that stops here is the failure this lane was written after. The module will validate and
still look like a different product.

## Step 4 · The instructional enhancement pass — mandatory

**Every substantial teaching screen gets this, not just the ones that look broken.** For each
concept:

1. What is being taught?
2. What should the learner *notice*?
3. Is text the best representation of it?
4. Would learning improve with a real image, an annotation, a technical schematic, a full-stage
   visual, a progressive reveal, a process or state-change animation, a comparison, a hotspot, a
   slider, a sequence, a decision interaction, an interactive figure, a mini-simulation, or a
   practical/task interaction?
5. **Is the current representation being preserved only because it already exists?**

Question 5 is the one that does the work. If the answer is yes, that is not a reason.

`course-visuals/decide/GUIDE.md` owns the mapping from learning need to representation. Use it.

**If a stronger representation is supported by the available evidence, build it.** Do not report
"animation recommended", "a visual could be improved" or "an interaction could be added" when the
evidence is sufficient to build the thing safely. A recommendation the operator has to action
themselves is the outcome this lane exists to stop.

Where the evidence is *not* sufficient — a safety-critical photograph nobody has, a figure that
needs a source the course does not carry — raise `GENERATED_ASSET_REQUIRED` or
`REAL_PHOTO_REQUIRED` with the brief, and say plainly what is blocked.

## Step 5 · Animation and interaction — search, do not wait

The animation law is unchanged (**L13**, owned by `course-visuals`): motion earns its place only
when it explains movement, process, flow, mechanism, sequence, state change, cause/effect or
before/after system behaviour. Decorative motion is still a defect.

What changes in retrofit is that **you go looking.** Do not wait for "add an animation here". A
static cross-section shows the parts; only a stepped reveal shows the causation. If a dynamic
representation clearly teaches the concept better and the evidence supports it, propose it and
build it.

## Step 6 · Existing visuals — keep the claim, rebuild the implementation

A technically meaningful visual is **evidence of a teaching decision**. Preserve the decision.

> **Right.** The star/delta figure claims the supply never moves and only the bridges change. Keep
> that claim and that interaction; rebuild it larger, clearer, better composed.
>
> **Wrong.** A small SVG exists, therefore keep that exact SVG and centre it.

Same for diagrams, animations, figures, task mechanics and process visuals. Ask what the visual
*claims*. If the claim is sound it survives; if the only argument for the implementation is that it
is already there, that is not an argument.

## Step 7 · Screen count follows the learning need

Split an overloaded screen. Merge two redundant ones. Add a dedicated visual, animation or debrief
screen. Move supporting detail to the handout as self-study.

**Do not add filler. Do not target the GAS BASIC screen count. Do not cut real teaching to look
leaner.** Minutes are locked (Track A, exact); screens are not. A thirteen-screen module that
teaches better as seventeen becomes seventeen.

## Step 8 · Verify — everything the new-build path runs, plus two

Nothing here is relaxed. Retrofit freedom is about *delivery design*; it removes no programme,
evidence or safety control.

```bash
python hours/scripts/check_balance.py <module.html> --programme <programme.json>
python ../course-module-ux/measure/scripts/check_navigation.py <course>
python ../course-module-ux/measure/scripts/check_static.py all <module.html>
python ../course-module-ui/scripts/audit_ui.py <course>
python ../course-visuals/scripts/check_visuals.py <course>
python retrofit/scripts/check_language.py <course> --declare <LANG>   # retrofit adds this
```

and in a browser, over http, at **1280×800 and 800×1280**:

```js
await AuditDrive.run()        // the render
await AuditCompose.run()      // composed, or merely fitting
GBVerifyFigures.run({})       // every figure actually rendered
```

Re-run `classify_module.py` at the end. **A retrofit that started at C and still classifies C has
not finished.**

## Step 9 · The acceptance question

> If the course title and subject were hidden, would a reviewer believe this module and GAS BASIC
> were produced by the same NOVIKONTAS Course Factory?

Judge composition, visual rhythm, typography, spacing, shell, interaction language, animation
quality, activity screens, technical visual scale, tablet behaviour, overall polish.

**Matching tokens alone is not enough.** A module can use every correct colour and still read as a
different product.

---

## Report

Into `factory-notes.md`, in the operator's language:

- COURSE_LANGUAGE, how it was determined, and the drift-check result
- the classification, its score, and the signals that drove it
- **what was preserved and why** — the content-lock side, itemised
- **what was rebuilt and why** — the delivery side, itemised
- every representation upgrade, with what it teaches that the old one did not
- anything raised as `GENERATED_ASSET_REQUIRED` / `REAL_PHOTO_REQUIRED` and what it blocks
- the before/after classification
- every honesty marker
