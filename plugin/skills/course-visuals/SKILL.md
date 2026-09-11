---
name: course-visuals
description: >
  Decide WHAT REPRESENTATION TEACHES A CONCEPT, then source or build it. Use whenever a course
  screen needs a picture, diagram, schematic, animation, chart, cutaway or interactive figure —
  and to decide when it needs none. Owns the learning-need-first decision, the visual storyboard,
  the instructional-animation law (motion must explain a mechanism, flow, state change, sequence
  or cause and effect — decorative motion is rejected), the four-level asset pipeline
  (project → factory → internet → create), provenance and licence records, RIGHTS_REVIEW_REQUIRED,
  GENERATED_ASSET_REQUIRED, and the visual quality gate that asks whether a figure actually
  teaches. Trigger on "add a diagram", "animate this", "we need an image of", "make this visual",
  "draw the system", "this looks like generic AI slop", "find a photo of", "is this animation
  worth it", "storyboard the visuals", or any request for a graphic in a course. Course-agnostic.
  NOT the palette, typography or card styling (course-module-ui), NOT screen composition, fill or
  overflow (course-module-ux), NOT how a trainee answers (course-task-ux), and never what a module
  teaches.
---

# Course visuals — what representation actually teaches this?

**v1 (2026-09-10) · plugin `course-factory` 2.1.0**

Technically working HTML is not the bar. A screen can validate, fit, contrast correctly and still
teach nothing. This skill exists because the default output of a language model asked for a course
graphic is a row of cards, three boxes joined by arrows, an icon, a gradient and something that
pulses — and none of those is a representation of anything.

**The acceptance test.** Point at any figure in a finished module and ask: *what can the learner do
now that they could not before?* If that sentence cannot be said out loud, the figure should not
have been built.

---

## The one law: learning first, format second

**Never start from "what visual goes here". Start from what the learner must understand.**

1. **Name the learning need** — `decide/knowledge/learning-needs.json` lists the fifteen:
   physical appearance · location · internal structure · system relationships · flow · sequence ·
   state change · mechanism · cause and effect · comparison · hazard · trend · decision ·
   troubleshooting · procedure.
2. **Only then choose the representation** — `decide/knowledge/representations.json` gives the
   candidates for that need, what each costs, and how each behaves on a tablet.
3. **Record the decision** in the storyboard, including a decision of *no visual*.

**Plain text is a valid outcome.** A definition, a limit, an exact regulatory phrase, a set point —
text carries those precisely and a picture only decorates them. Never add a visual to fill space or
to make a screen look finished. An empty area is cheaper than a misleading figure.

---

## Pick the mode, then read one lane

| Mode — what the task actually is | Read |
|---|---|
| Choosing what a concept should look like; storyboarding a module's visuals | `decide/GUIDE.md` |
| Finding or creating the actual asset; licences, provenance, rights | `source/GUIDE.md` |
| Judging whether a built visual teaches; signing one off | `review/GUIDE.md` |

Never load a lane the mode does not need.

### Deliberately outside this skill — point at these, never copy them

| Concern | Owned by |
|---|---|
| Palette, typography, card/pill/photo styling, semantic colour, the token set | `course-module-ui` |
| Screen composition, fill, overflow, contrast, tap size, the one-page deck, the run script | `course-module-ux` |
| How a trainee answers, scores, or completes anything | `course-task-ux` |
| Hours, ILOs, build order, coverage | `course-factory` |
| What a module teaches, and whether a claim is true | `course-evidence` when it exists; until then the operator's sources |

The division that matters: **`course-module-ui` owns how a page looks like a NOVIKONTAS page.
This skill owns what the picture on it should be.** A figure obeys the token set; the token set has
no opinion on whether the figure should have been a photograph.

---

## The animation law — L13, and this skill owns it

> **Animation is instructional only when it explains movement, flow, state change, sequence,
> mechanism, cause and effect, spatial relationship, progression over time, or system response.**
> **Decorative motion is not instructional animation.**

Every substantial animation answers all four questions **in the storyboard, before it is built**:

1. **What changes?**
2. **Why does it change?**
3. **What should the learner notice?**
4. **What should the learner understand afterwards, that they did not before?**

**The failure signature:** if question 4 is answered by the caption alone, with the motion removed,
the motion is not carrying the teaching. Ship the caption and a static figure.

Rejected by name — `review/knowledge/motion-rules.json` carries the full list and the reasons:
random floating · decorative pulsing · bouncing icons · unnecessary fade sequences · moving arrows
without an explained process · meaningless autoplay loops · parallax and scroll reveal ·
**motion added only because animation was requested**.

Every non-chrome animation **declares its category** in the markup — `data-motion="teaching"`,
`"affordance"` or `"ambient"`. An animation that cannot be categorised is not built. Ambient motion
is capped at one effect per screen and is banned on a screen that carries a teaching animation.

---

## Technical honesty — L12, and this skill owns it too

**Simplification is allowed. Misleading simplification is not.**

Dropping a branch to keep a schematic readable is simplification. Drawing a branch that does not
exist, implying a flow direction that is wrong, or joining two components that are not connected is
an error wearing the costume of a diagram.

For anything with topology — a cargo system, a circuit, a fixed installation — do **not** render
`[BOX] → [BOX] → [BOX]` when the real arrangement teaches better. Show, where relevant: component
identity · approximate physical or system relationship · connection · flow direction · active and
inactive state · changing conditions · the labels the learner is asked about · cause and result.

**Every asset carries provenance, a licence and a visual verification**, in a metadata file beside
the file. Open and look at every image before using it, and record that you looked. A plausible
photograph of the wrong equipment teaches false recognition and is worse than no photograph.

Never present a generated illustration as a photograph, an interpolated value as a measured one, or
one manufacturer's equipment as another's.

---

## The storyboard gate

**For a substantial module or a complex concept, the storyboard is approved before any figure is
implemented.** Not for a trivial screen — a single labelled photograph does not need paperwork.

Per important concept: learning purpose · representation · source strategy · interaction or
animation (with the four questions, if any) · implementation technology · **why this representation
is appropriate**.

Copy `templates/VISUAL_STORYBOARD.md`. The gate exists to stop the jump straight from text into
generic HTML, which is where the card grids come from.

---

## The asset pipeline — in order, and a level is only exhausted when it has been searched

`source/knowledge/asset-pipeline.json` is the authority. The short form:

**1 PROJECT** — `source_files/`, operator-supplied assets, manuals, drawings, the course's own
existing assets. Search by more than the requester's phrasing: equipment name, manufacturer,
alternate and older terminology, system name, likely figure captions, abbreviations, both
spellings. *One failed grep is not a search.*
**2 FACTORY** — `${CLAUDE_PLUGIN_ROOT}/resources/`. Reuse only if technically **and** pedagogically
right; a near-miss reused to save time teaches the near-miss.
**3 INTERNET** — only after 1 and 2 were actually searched. Manufacturer → official organisation →
original manual → recognised technical body → other credible source. **Not** SEO farms, aggregators,
scraped image sites or blogs. Record source, origin, rights, relevance, intended use, whether
modification is permitted, whether attribution is required. **Legally usable assets are downloaded
and packaged locally** — the tablet has no network and the app 403s every external host.
**4 CREATE** — SVG for anything with topology, labels or state; HTML/CSS/JS for state-driven
process; Canvas only where SVG genuinely fails; a generated illustration only when a realistic
scene is the right medium. **Never generated imagery in place of a structured technical schematic.**

Two escalations, and neither is silent:

- **`RIGHTS_REVIEW_REQUIRED`** — rights unclear or restricted. **Blocks shipping.** An uncleared
  publisher figure has already blocked a whole course in this system once.
- **`GENERATED_ASSET_REQUIRED`** — nothing suitable exists at any level. Emit the full generation
  brief in `source/schemas/GENERATED_ASSET_BRIEF.md`. There is no image-generation MCP yet; the
  brief is the contract for when there is.

`scripts/resolve_asset.py` runs levels 1 and 2 mechanically. Level 3 is judgement and belongs to the
**`visual-sourcer`** agent, which works in isolated context and returns a short report.

---

## Tablet-first, always

Touch-first · large labels · large controls · **no hover dependency** · no precision pointing ·
robust in landscape and sane in portrait · minimal typing · annotations readable at arm's length ·
offline-safe · **no remote runtime asset**.

An SVG label authored at font-size 10 in a 1000-unit viewBox is 3.8 px inside a 380 px column.
Measure the *rendered* size, not the viewBox units. `review/knowledge/visual-floor.json` has the
numbers; `course-module-ux` owns the screen floor and this skill does not restate it.

---

## Variety is a teaching decision

Consistent across the course: typography, tokens, interaction quality, navigation, feedback,
accessibility, semantic colour, quality level.

**Not consistent: the representation.** An electrical circuit, a cargo piping system, a firefighting
procedure and a human-factors scenario should not reach for the same layout mechanic. If three
screens in a row use the same interaction, that is a finding, not a house style.

---

## Verify before reporting done

1. `scripts/check_visuals.py <files or dirs>` — the deterministic half: undeclared decorative
   motion, missing reduced-motion guard, tiny SVG labels, remote assets, missing alt, box-and-arrow
   chains, text-in-cards screens with no figure, disallowed file types.
2. `scripts/check_assets.py <assets dir>` — provenance: every image has a metadata entry, every
   entry has its required fields, `visually_verified` is real, rights states are valid, and nothing
   sits at `RIGHTS_REVIEW_REQUIRED`.
3. `scripts/verify_figures.js` **in the page**, over http — `run()` proves each figure
   rendered at all, and `await motion()` proves it is alive: `MOVES`, `RESPONDS` or `STATIC`.
   Only `STATIC` fails. A figure that answers its own toggle, slider or tap is doing its job
   and must not be reported as a picture. Always read the `scheduler` field — a hidden page
   suspends `requestAnimationFrame`, and a probe that cannot see frames must never be read as
   a verdict about the course (L20).
4. `review/GUIDE.md` — the half no script can do. **A visual does not pass because the HTML
   validates.** Fourteen named failure modes, and one question: *does this actually teach?*

Then write `templates/visual-notes.md` next to the module: every representation chosen and why,
every asset with its source and rights, every animation with its four answers, every
`RIGHTS_REVIEW_REQUIRED` and `GENERATED_ASSET_REQUIRED`, and feedback on this skill.

## Honesty markers

The family set — `UNKNOWN`, `PLACEHOLDER`, `PROVISIONAL`, `[VERIFY: …]` — plus two of this
skill's own:

| Marker | Means |
|---|---|
| `RIGHTS_REVIEW_REQUIRED` | rights unclear or restricted. Blocks shipping. Owner decides. |
| `GENERATED_ASSET_REQUIRED` | no suitable asset exists at any level; a generation brief is attached. |

Every marker written into an artefact must also appear in the notes file.
