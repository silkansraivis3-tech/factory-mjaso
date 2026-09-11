# Retrofit — the second workflow

Plugin **2.4.0**. The Factory now has **two** creative workflows that converge on the same product.

| | starts from | does |
|---|---|---|
| **NEW BUILD** | an authoritative programme and content | design the teaching delivery from scratch |
| **RETROFIT** | an authoritative existing course | keep the content; **rebuild the delivery** |

---

## The failure this was written after

A colleague asked for an existing module to be brought up to GAS BASIC quality. What came back was
a technically correct retrofit that still felt weaker than GAS BASIC.

Nothing was broken. The shell migrated, the tokens applied, the navigation worked, the QA passed.
Claude had treated the existing HTML as something to **preserve** — and every individual decision
to keep a layout was defensible.

**Conservatism looks like diligence.** That is exactly why it could not be left to judgement:

> **PRESERVE THE COURSE CONTENT.**
> **DO NOT PRESERVE THE EXISTING DELIVERY IMPLEMENTATION BY DEFAULT.**

The existing module is **source material plus learning intent**. It is not the presentation
template, and "the HTML works" is not an argument for keeping it.

Recorded as **L18** in `FACTORY_LAWS.md`; the authority is
`course-factory/retrofit/knowledge/content-lock.json`.

| Locked — needs explicit authorisation | Free — redesign on the evidence |
|---|---|
| technical meaning · programme requirements · ILOs · **official hours** · assessment intent · intended practical exercises · course terminology · source-supported facts · **COURSE_LANGUAGE** | screen count · screen order · HTML · layouts · card arrangements · density · progressive disclosure · visual implementation · animation · interactive mechanics · task presentation · navigation · CSS/JS · hierarchy · composition |

An existing visual is **evidence of a teaching decision**. Preserve the decision; the implementation
is free. The star/delta figure's claim — *the supply never moves, only the bridges change* —
survives; its small SVG does not have to.

---

## Cowork-first routing

The operator may be a non-technical colleague. They should not need git, a terminal, a skill name,
an agent name, a validator name or the folder architecture. **This sentence has to be enough:**

> "Redesign Module 1 using the NOVIKONTAS Course Factory."

The triggers live in `retrofit/knowledge/routing.json` and in the entry skill's own frontmatter —
the only surface a free-form sentence is actually matched against. Nine phrasings are asserted in
the test suite, plus the same intent in Latvian and Russian.

**RESTYLE is not RETROFIT.** A restyle needs **both** a narrow cosmetic target *and* a scope
limiter:

- *"only change the colours"* → restyle. Do exactly that, say in one line what a full retrofit
  would additionally do, and stop.
- *"change the colours and make it like GAS BASIC"* → retrofit.

Doing more than was asked is not generosity.

---

## What a retrofit actually runs

`retrofit/GUIDE.md` is the lane; `knowledge/build-order.json` → `retrofit_order` is the order.

1. **COURSE_LANGUAGE** — detect, state, lock
2. **Authoritative record** — programme, ILOs, hours: *read*, never rewritten
3. **Classify the delivery** — A, B or C, decided here and not asked of the operator
4. **Content inventory** — what each screen *claims*; this is what survives
5. **System migration** — shell, tokens, composition, engine *(necessary, never sufficient)*
6. **Instructional enhancement pass** — mandatory, every substantial teaching screen
7. **Composition pass** — a composition per screen; split, merge or add as the learning needs
8. **Tasks** — when the module has them
9. **Verify** — every new-build check, plus the language check and a **re-classification**

> A retrofit that started at C and still classifies C has not finished.

### The classification

`retrofit/scripts/classify_module.py` scores six signals — canonical shell, composition vocabulary,
teaching visuals, activity screens, tablet behaviour, token adherence — and returns:

- **A** preserve mostly as-is · **B** moderate delivery redesign · **C** substantial redesign

**Classify on delivery quality, never on whether the HTML works.** Valid markup, resolving links and
green checks sit in the spec's `not_signals` list precisely so nobody reaches for them.

Measured, for calibration:

| | score | level |
|---|---|---|
| GAS BASIC Module_01 — the design authority | 0.80 | **A** |
| ETPB3 after Phase 4C | 0.81 | **A** |
| GAS BASIC Modules 03/04/07/08 | 0.67–0.75 | B |
| synthetic: valid HTML, careful prose, no system | 0.21 | **C** |

### The instructional enhancement pass

Every substantial teaching screen, not just the broken-looking ones. What is taught · what should
the learner notice · is text the best representation · would it improve with an image, annotation,
schematic, full-stage visual, progressive reveal, process or state-change animation, comparison,
hotspot, slider, sequence, decision interaction, interactive figure, mini-simulation or task —
and the question that does the work:

> **Is the current representation being preserved only because it already exists?**

If a stronger representation is supported by the evidence, **build it**. Do not report "animation
recommended" when the evidence is enough to build it safely. Where the evidence genuinely is not
there, raise `GENERATED_ASSET_REQUIRED` / `REAL_PHOTO_REQUIRED` and say what is blocked.

The animation law (**L13**) is unchanged — motion must explain movement, process, flow, mechanism,
sequence, state change or cause/effect. What changes is that retrofit goes **looking**.

### Screen count follows the learning need

Split an overloaded screen, merge redundant ones, add a dedicated visual or debrief screen, move
supporting detail to the handout. **No filler. No targeting the GAS BASIC screen count. No cutting
real teaching to look leaner.** Minutes are locked; screens are not.

---

## COURSE_LANGUAGE — L19

Mandatory in every mode. Course-facing output — slides, tasks, handout, assessment, feedback,
instructor cues, practical cards, START_HERE, run script — stays in COURSE_LANGUAGE unless
translation is **explicitly** requested. The chat report, companion file, comments and validator
output follow the operator.

A Latvian operator asking, in Latvian, to redesign an English module gets **a Latvian report and an
English module.** Translating an accredited artefact because the request arrived in another
language destroys it, and it happens one screen at a time.

`retrofit/scripts/check_language.py` is the drift check — script, diacritics and function-word
profile over course-facing files only. It correctly reads GAS BASIC as English and ETPB3 as
Latvian, and flags all nine ETPB3 files when English is declared.

---

## Tests

`retrofit/scripts/test_routing.py` — **42 deterministic assertions** over the three knowledge files.

It tests the **rules**, by implementing them. It does not test the model's free-form judgement;
nothing in a script can, and pretending otherwise would be the green-exit-as-proof this factory
keeps recording.

The owner's five cases, all asserted:

| | case | expected |
|---|---|---|
| A | existing English module + Latvian operator request | RETROFIT, course stays English |
| B | technically valid but visually weak HTML | not preserve-as-is → C |
| C | useful interactive figure, weak layout | concept preserved, implementation free |
| D | 13 screens where stronger teaching needs 17 | allowed |
| E | "only change the colours" | RESTYLE, not RETROFIT |

**Mutation-tested.** Removing the `only` scope limiter, and removing `the HTML parses` from
`not_signals`, each produce exactly one failure. A suite that cannot fail is not a suite.

### Two things the classifier got wrong before it was right

1. It scored the shell and the tokens on **filenames**, and classified **GAS BASIC Module_01 — the
   design authority — as "needs moderate redesign"**, because it loads `presentation.css` rather
   than `gb_shell.css`. Those files were extracted *from* it. Both signals now measure the system:
   the shell's structural landmarks wherever they live, a declared token set wherever it is
   declared.
2. It scored composition against **our** vocabulary and marked the golden down for using
   `exp-stage`, `sil-row` and `handover` — the names ours was derived from. Any modifier class on
   `.slide-body` now counts.

A classifier that marks the reference standard as weak is not conservative. It is wrong, and it
would have sent a colleague to rebuild the thing the rest of the system copies.

---

## Nothing was relaxed

Retrofit freedom is about **delivery design**. It removes no programme, evidence or safety control:
canonical shell and composition, navigation checks, figure runtime checks, composition QA, Track A
hours exact, the Track B activity metric, no links inside presentation screens, the runtime render
sweep, tablet QA, and the version bump for every content release — all unchanged and all re-run.

One regression was found and fixed on the way: `pass_complete.html`, the UI checker's PASS control,
had gone stale when 2.3.0 split `gb_shell.css`, and was reporting 8 defects. The fixture was wrong,
not the checker — **a fixture is only a control if it is kept current.**
