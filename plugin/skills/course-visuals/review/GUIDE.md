# Review — does this visual actually teach?

Read this at sign-off. `knowledge/visual-floor.json` carries the numbers and the checklist;
`knowledge/motion-rules.json` carries the motion categories and the reject list.

---

## The premise

> **A substantial visual does not pass because the HTML validates, the links work, the CSS fits and
> no JavaScript errors occur.**

Those checks belong to `course-module-ux` and they are necessary. They are not sufficient, and they
have never once caught a card grid.

This review asks the question none of them can: **does this visual actually teach?**

---

## Run the deterministic half first

```bash
python scripts/check_visuals.py <file-or-dir> [...]
python scripts/check_assets.py <assets-dir> [...]
```

`check_visuals.py` finds: undeclared decorative motion · infinite animation with no
reduced-motion guard · SVG labels below the rendered floor · remote asset references · images with
no alt or aria-label · box-and-arrow chains · text-in-cards screens carrying no figure at all ·
file types the tablet cannot serve.

`check_assets.py` finds: images with no provenance entry · entries missing required fields ·
`visually_verified` that was never really done · invalid rights states · anything sitting at
`RIGHTS_REVIEW_REQUIRED` · orphan entries describing files that no longer exist.

Both are **advisory on judgement and hard on facts**. A decorative-vocabulary match is a question
put to a human; a remote asset reference is a failure.

**A clean run is not a pass.** It means nothing mechanical is wrong. Now look at the thing.

---

## The human half — fourteen questions

`knowledge/visual-floor.json` → `human_review_questions`. Ask them of each substantial figure. The
first is the one that matters most.

1. **Generic AI appearance** — could this screen belong to any course on any subject? If the subject
   were swapped, would only the words change?
2. **Unnecessary cards** — are these carrying a relationship, or are they a paragraph with borders?
3. **Text that should be visual** — is a spatial, sequential or causal relationship being described
   in a sentence instead of shown?
4. **Visual that should be text** — does the figure restate the sentence beside it without adding
   location, relationship or change?
5. **Decorative animation** — remove the motion. Is anything lost?
6. **Weak hierarchy** — what does the eye land on first? Is that the thing that matters?
7. **Misleading relationships** — does the drawing imply a connection, direction or order the real
   system does not have?
8. **Tiny labels** — read it at arm's length on the tablet, not zoomed on a desktop.
9. **Low resolution** — soft, upscaled, or a screenshot of a screenshot?
10. **Awkward crop** — subject cut, off-centre, or competing with background clutter?
11. **Tablet readability** — landscape **and** portrait. Anything overlapping, clipping, or
    reflowing into a stripe?
12. **Repeated mechanic** — is this the same interaction as the previous three screens?
13. **Fake complexity** — does it look sophisticated while carrying two facts?
14. **Technically ambiguous** — could a subject-matter expert read it two ways? In a technical
    figure, ambiguity is an error, not a style.

### The one-sentence test

Before any verdict, finish this sentence about the figure:

> *"After this, the learner can ______, which they could not before."*

If it cannot be finished, the verdict is `REJECT` regardless of how good the figure looks.

---

## Reviewing an animation

Beyond the fourteen:

- **Does it carry its four answers?** If question 4 is answered by the caption alone with the
  motion removed, ship the caption and a static figure.
- **Is the category declared?** `data-motion="teaching" | "affordance" | "ambient"`. Undeclared
  non-chrome motion is a finding.
- **Is it controllable?** Play, pause, step, replay — all ≥ 44 px. A teaching animation the
  instructor cannot pause is unusable in a room.
- **Is the resting state readable?** Stop it. Can the screen still be taught from?
- **Does it stop off-screen?** A loop running behind a slide the class is not on wastes battery and
  desynchronises replay.
- **Ambient budget** — at most one ambient effect per screen, and none on a screen carrying a
  teaching animation.
- **Reduced motion** — ambient stops under `prefers-reduced-motion: reduce`; teaching motion may
  remain but must not autoplay.

---

## Reviewing a technical figure

- **The topology test** — could the learner say what happens downstream if one element is shut?
- **Direction** — is every flow direction correct, and is it shown rather than asserted?
- **State** — are active and inactive distinguishable without colour alone?
- **Labels** — is everything the learner is asked about actually labelled?
- **Honest simplification** — what was dropped, and does dropping it change what the learner would
  conclude? Dropping a branch is fine; inventing one is not.
- **Drawing declared** — if it is a drawing of something no camera can see, does the page say so on
  its face?
- **Sourced values** — on a chart, is every plotted value traceable, and is interpolation marked?

---

## Verdicts

| | |
|---|---|
| **PASS** | teaches something nameable, technically unambiguous, readable on the tablet, motion declared and earned |
| **REWORK** | the learning need is right, the representation or execution is not — say which, and name the representation to try instead |
| **REJECT** | the visual should not exist — plain text serves the need better, or the right asset does not exist yet |
| **BLOCKED** | `RIGHTS_REVIEW_REQUIRED`, or the asset is missing — not a quality verdict, and not the author's to clear |

A `REWORK` that does not name the replacement representation is not a review, it is a complaint.

---

## Reporting

Report what failed as plainly as what passed. For each finding: the file, the figure, the named
failure mode, and what to do instead.

Then fill `templates/visual-notes.md` — every representation chosen and why, every asset with its
source and rights, every animation with its four answers, every marker, and feedback on this skill.
A marker used in an artefact and never reported is the failure that section exists to stop.
