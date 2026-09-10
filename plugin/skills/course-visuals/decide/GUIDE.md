# Decide — what representation teaches this concept

Read this when you are choosing what a concept should look like, or storyboarding a module's
visuals. `SKILL.md` carries the laws; this is the procedure.

---

## The sequence, and it does not reorder

```
1  What must the learner UNDERSTAND?        -> a named learning need
2  What can carry that need?                -> candidate representations
3  Does an asset for it exist?              -> the source lane, levels 1-2
4  What will it cost to build?              -> technology, and whether it is worth it
5  Record the decision, with its reason     -> the storyboard
6  Approve the storyboard                   -> only then implement
```

Step 1 is the one that gets skipped, and skipping it is how a screen ends up with three cards.

---

## 1 · Name the learning need

`knowledge/learning-needs.json` is the authority. Fifteen needs, each with the question it answers,
its strongest representations, what to avoid for that need, and a test.

Say it as a sentence before going further:

> *"The learner must understand **where the pressure relief valve sits relative to the tank dome**,
> so they can find it on a ship they have not seen."* → **location**

> *"The learner must understand **why the pressure rises when the temperature rises**."* → **mechanism**

> *"The learner must know **the exact wording of the entry criterion**."* → text. There is no visual
> here, and that is the finding.

**If the need cannot be named, there is no visual to design.** Either the text is unclear — fix the
text — or the screen is trying to look busy.

### Two needs on one screen

Split them. A screen carrying both *what it looks like* and *how it works* teaches neither well.
The reference course's strongest pattern is **explain first, then show**: an explanation screen,
then a separate visual screen. Where text and animation compete for attention, they both lose.

---

## 2 · Choose the representation

`knowledge/representations.json` lists every representation this factory may use, what it teaches,
what technology it needs, which pipeline level it comes from, and how it fails.

Work down the candidates for the named need and take the **first one you can actually source or
build correctly**. A weaker representation done honestly beats a stronger one faked.

### The six rejected non-representations

These are what gets produced when step 1 was skipped. `representations.json`
→ `rejected_representations` carries the reasons. Named so a review can point at the name:

**card grid of prose** · **box-and-arrow chain** · **decorative icon row** · **gradient hero** ·
**SmartArt pyramid or cycle** · **stock photograph of people**

None of them is a representation of anything. A card is a legitimate *component*
(`course-module-ui` owns it) — using cards as the *answer to a teaching need* is this skill failing
to name the need.

### The topology test

If the subject has parts that connect, ask: **could the learner say what happens downstream if one
element is shut?** If not, the diagram is not modelling the system.

A real system has services, headers, branches, direction and state. `[BOX] → [BOX] → [BOX]` asserts
a linearity that almost nothing has. Build the geometry from a **typed topology** — a data structure
naming each element, its kind, its endpoints and its state — and render from that, so the same model
can be re-laid-out, re-stated and checked. See `resources/patterns/system-schematic/`.

### The animation gate

If the candidate is an animation, answer the four questions **now**, in the storyboard, not after
building it. `review/knowledge/motion-rules.json` § `four_questions`.

Then declare the category: `teaching`, `affordance` or `ambient`. If you cannot, do not build it.

The commonest legitimate case is **mechanism**: several properties changing together, causally —
a temperature rising *and* a needle moving *and* a level changing, one cause, three visible effects.
That is worth animating. A thing appearing is not.

The second is **correcting a misconception**. The strongest sequence in the reference course spends
one of its seven steps on *"never assume the vapour is inside the visible cloud"* — the animation
exists to break a wrong mental model the learner arrives with. If you can name the misconception,
you can usually name the animation.

---

## 3 · Check whether the asset exists before designing around it

Do not design a screen around a photograph that does not exist. Run levels 1 and 2 —
`scripts/resolve_asset.py`, or the `visual-sourcer` agent for anything needing judgement — and let
the answer shape the storyboard.

If the answer is `GENERATED_ASSET_REQUIRED`, that is a legitimate storyboard entry. Write the brief,
record the marker, and design the screen so the figure can drop in later without a rewrite.

---

## 4 · Choose the technology honestly

| Need | Reach for |
|---|---|
| topology, labels, state, anything a reviewer must check | **inline SVG** |
| discrete states the learner drives | **HTML/CSS/JS** |
| a real object the learner must recognise | **photograph**, annotated with a live overlay |
| what no camera can see | **cutaway or authored drawing**, declared as a drawing on its face |
| a relationship between two quantities | **sourced chart**, interpolation marked |
| element count or per-frame maths that genuinely defeats SVG | **canvas**, and accept the cost |

**Inline SVG is the default for authored figures** because it is themeable, annotatable,
translatable, diffable and visible to every check in this factory. A PNG of a diagram is none of
those.

**Canvas is a signal to re-read the need.** The reference course, eight modules of technical
teaching material, uses canvas in **zero** teaching visuals. If you are reaching for it, check you
have not over-specified the figure.

---

## 5 · Storyboard

Copy `templates/VISUAL_STORYBOARD.md`. One row per important concept:

| # | Concept | Learning need | Representation | Source strategy | Interaction / animation | Technology | Why this representation |
|---|---|---|---|---|---|---|---|

**Required for:** a substantial module, any complex concept, anything animated, anything that needs
a new asset.
**Not required for:** a single labelled photograph, a plain-text screen, a figure being reused
unchanged from the factory library.

The storyboard is approved before implementation. Changing a row is free; rebuilding six figures is
not — the same economics as the screen inventory in `course-module-ux`.

### Variety, checked at storyboard time

Read the finished column of representations down the page. If the same mechanic appears three times
in a row, that is a finding to fix **now**, while it is still a table. Subject matter should drive
the representation: a circuit, a piping system, a procedure and a human-factors scenario have
different shapes and should not look alike.

---

## What "done" looks like for this lane

- Every important concept has a named learning need, in a sentence
- Every representation choice has a reason that refers to the need, not to appearance
- Every animation has its four answers and a declared category
- Every asset has a pipeline level and, where already known, a rights state
- Concepts decided as **plain text** are recorded as decisions, not omitted
- The storyboard is approved before any figure is implemented
