# `GENERATED_ASSET_REQUIRED` — the generation brief

Emitted when levels 1–3 of the asset pipeline found nothing suitable **and** a realistic or
illustrative image is genuinely the right medium for the learning need.

**There is no image-generation MCP in this plugin.** This brief is the contract for when there is
one, and it is useful immediately — a human can take it to any generator, or commission a
photograph or an illustrator from it.

**A brief missing any field is not a brief.** The two that get left empty are *forbidden
inaccuracies* and *what must be visible*, and they are the two that stop a generated image teaching
something false.

---

## Before writing one — three gates

1. **Would a technical schematic teach this better?** If the need is system relationships, flow,
   internal structure or mechanism, the answer is almost always yes. Author SVG instead.
   *Generated imagery never replaces a structured technical schematic.*
2. **Is this safety-critical equipment the learner must recognise in real life?** If yes, **stop**.
   A plausible invention teaches false recognition. Escalate for a real photograph.
3. **Did levels 1–3 actually get searched?** Record the terms tried.

---

## The brief

```markdown
# GENERATED_ASSET_REQUIRED — <short-name>

## 1 · Learning purpose
What the learner must understand, in one sentence, from learning-needs.json.
Named need: <one of the fifteen>

## 2 · Subject
The single subject of the image. One subject per image.

## 3 · Technical requirements
Every fact the image must get right: proportions, arrangement, count, orientation,
relative scale, the state the equipment is in. Cite the source for each where one exists.

## 4 · Composition
What is in frame and where. Foreground, middle, background. What is deliberately excluded.

## 5 · Viewpoint
Eye level, elevation, angle, distance. Say it as a camera position, not as a mood.

## 6 · Required visible components
A list. Each item must be identifiable in the result, because each is either labelled
later in HTML or is the thing the learner is asked to find.
- [ ] ...
- [ ] ...

## 7 · Forbidden inaccuracies
The errors a generator is LIKELY to make with this subject, named so they can be checked.
This is the most important field in the brief.
- must NOT show <the plausible wrong thing>
- must NOT invent <the detail that would be false>
- must NOT resemble <the different piece of equipment it will drift towards>

## 8 · Visual style
Photographic, technical illustration, cutaway illustration, or schematic-realistic.
State it plainly. If photographic realism would make it mistakable for a real photograph
of real equipment, choose illustration instead and say why.

## 9 · Aspect ratio and resolution
Aspect: <e.g. 16:9 / 4:3 / 1:1>
Target long edge: >= 1200 px, <= 2200 px

## 10 · Background
Plain, contextual, or transparent. If the image is going onto a dark slide, say so —
a white background will be framed in white and look wrong.

## 11 · Intended HTML placement
Which screen, which module, full-bleed or inset, and whether an overlay will sit on it.

## 12 · Text and labels
NONE in the generated pixels. List the labels that will be added afterwards in HTML/SVG,
and reserve the space they need.
- label: "<text>" at approximately <where>
- ...

## 13 · Provenance to record on delivery
origin: generated illustration
generated_by: <model or tool>
generation_brief: <path to this file>
depicts_what_no_photograph_can: <one line>
declared_as_drawing_on_page: true
```

---

## Rules that survive into the delivered asset

- **Labels are never generated into the pixels.** They are added in HTML or SVG afterwards, so they
  stay translatable, themeable, legible at tablet scale, and correctable without regenerating.
- **The page says on its face that it is an illustration.** A generated image presented as a
  photograph is a lie the learner cannot detect.
- **The result is verified like any other asset** — opened, looked at, checked against §7, and
  `visually_verified` filled in honestly. A generated image that got §7 wrong is rejected, not
  captioned around.
- **`_figure_meta.json`** carries `origin`, `generated_by`, `generation_brief`,
  `depicts_what_no_photograph_can` and `declared_as_drawing_on_page`.

---

## When the brief comes back unfulfilled

If no generator can satisfy §7, that is a real answer. Record it, mark the concept
`PLACEHOLDER`, design the screen so the figure can drop in later, and tell the owner what would
unblock it — usually a photograph somebody has to take.
