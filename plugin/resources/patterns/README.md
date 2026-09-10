# patterns/

Three reusable visual engines, course-agnostic. Owned by `course-visuals`.

These are **implementation approaches extracted from the reference course**, not copies of it —
the mechanisms, generalised and cleaned, with none of its subject matter. Each exists because it
was invented once, worked, and was then copy-pasted between modules instead of shared. In the
reference course two modules each carry four **dead** visualisation engines, copied wholesale from
a third and self-disabling because their host elements do not exist. Shipping one canonical copy
is the fix.

| Pattern | Solves | Files |
|---|---|---|
| **photo-pins** | annotating a photograph so the annotation survives a re-crop | `cv_pins.js` · `cv_pins.css` |
| **stepped-process** | the default shape of a teaching animation | `cv_steps.js` · `cv_steps.css` |
| **system-schematic** | drawing a system from a typed topology instead of boxes and arrows | `cv_schematic.js` · `cv_schematic.css` |

All three: ES5, no dependencies, no build step, no CDN, safe on an old Android WebView, and every
colour taken from `course-module-ui`'s token set with a literal fallback.

---

## photo-pins

**The problem.** A label burned into a JPEG points at the wrong thing the moment somebody re-crops
the image, changes the aspect ratio, or swaps in a better photograph.

**The approach.** Pins carry their position as a percentage of the **photograph**
(`data-ix` / `data-iy`), and the script maps that through the `object-fit: cover` crop at paint
time. A pin whose target is cropped away hides itself rather than pointing at nothing. A pin near
an edge flips its label — and flips again to stay off a sibling copy column, because a label
printed across live body text is worse than a label on the wrong side.

**The dot never moves.** On a photo screen the dot *is* the answer; a label pushed away from its
dot would be the wrong fix.

## stepped-process

**The problem.** "Add an animation" produces something that moves and teaches nothing.

**The approach.** Layers carry `data-step` and are revealed cumulatively. One caption per step says
what changed and why. The instructor controls it — play, pause, step, replay — and nothing
auto-advances past the point being made. It pauses when it scrolls out of view, and honours
`prefers-reduced-motion` by not autoplaying while still allowing stepping.

**The test it is built around:** stop the animation. If the resting state cannot be taught from,
the figure is not finished.

Declare `data-motion="teaching"` on the figure. `course-visuals` rejects undeclared non-chrome
motion.

## system-schematic

**The problem.** `[BOX] → [BOX] → [BOX]`. It asserts a linearity real systems rarely have, and
hides topology, service, direction and state.

**The approach.** Declare the system as **data** — nodes with a kind and a position, segments with
a service, two endpoints and a state — and render from that. Components are drawn as themselves: a
tank shows its liquid level because the phase split is content, a valve uses the conventional
two-triangle body, a pump has an impeller arrow.

Two consequences worth the effort:

- **Flow is drawn along the real route** as a travelling dash, not asserted by a floating arrow.
- **The model can be queried.** `CVSchematic.downstream(sys, 'p1', ['v3'])` answers *what is still
  connected if V3 shuts* — so the author can check the figure against the real system instead of
  hoping. A hand-drawn picture of boxes cannot be asked anything.

State is shown by opacity **and** dash, never by colour alone.

---

## Using one

Copy the pair of files next to the module and reference them. Do **not** copy them into a course
pack per module — that is exactly the failure this folder exists to end. One copy, referenced.

```html
<link rel="stylesheet" href="../../shared/cv_steps.css">
<script src="../../shared/cv_steps.js"></script>
```

## Adding one

A pattern earns its place here when it has been used in **two** modules and the second one wanted
it unchanged. Before then it is module code. Anything added here must be course-agnostic, ES5,
dependency-free, token-driven, and documented with the problem it solves — not just what it does.
