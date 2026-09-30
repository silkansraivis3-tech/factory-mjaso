# Routing notes

*Moved here word for word from `course-factory/SKILL.md` in 2.11.0 (Phase 5, step 11) so the
skill file every session reads stays light. Nothing was deleted or reworded. What the orchestration and coverage lanes are for, and why the visual layer is routed to course-module-ui. Read it when choosing orchestrate or audit mode, or at build step 8.*

*Since 2.11.1 "paste" below means `course-module-ui/scripts/design_system.py install`: the style
files are copied by the script and never read; `course-module-ui/references/vocabulary.md` is what
to read.*

---

`orchestration/` answers "eight modules, eight agents at once — how?". It is the only lane that is
about the *run* rather than the course: what has to be decided before a fan-out (the minutes, the
module split, the language, the visual system, the task-code ranges), what the reader agent writes
to a **file and never to a slide** (`MODULE_MAP.md`, `ILO_MAP.md`), and the one rule that keeps a
parallel build from losing work — **one agent, one folder**, with everything shared assembled
afterwards by one process.

`coverage/` exists because the other two cannot see its failure. A course can have exact hours and
perfect wiring and still not teach an outcome. On GAS BASIC the topic-level record was green at
64 of 64 and had never once been checked against the model course's own 266 itemised outcomes —
where one real gap was waiting.

---

### The visual layer is routed, never improvised

When a new module reaches visual production, **route it to `course-module-ui`**. That skill is
the authority on the look; this one does not restate a single colour, radius or component rule,
and neither should you. It carries `knowledge/tokens.json` (the values),
`templates/gb_tokens.css` (paste, do not retype) and `references/anatomy.md` (the components).

GAS BASIC **Module_01 is the canonical visual reference** — the palette, the typography, the
light and dark/photo modes, the header band, card geometry, pills, spacing, radius, shadow, the
takeaway treatment, the semantic status colours. It is *not* a template to copy:

- **There is no canonical screen count.** Screens are derived from the learning need, the
  delivery method, the content depth and the practical work. Ten screens, twenty-five, fifty,
  almost no presentation, practical-only — all legitimate. Never add filler screens to resemble
  Module_01 numerically, and never cut real teaching to resemble it either.
- **Not every screen has to be interactive**, and low visible density is not low learning depth.
  Progressive disclosure, layered cards, diagrams and interactive figures teach without a wall
  of text. Compact (`course-module-ux` law 3) never means thin.
- What must match is the **system**: visual language, UI quality, UX behaviour, tablet-first
  delivery, the Start → Next → Next one-page model where it applies, component styling,
  responsive behaviour, visual hierarchy, task usability and functional quality.

`build-order.json` step 8 is the contract; `no_fixed_slide_count` and `density_is_not_depth` in
that file are the rules above in their authoritative form.
