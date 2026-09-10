# Course Factory — global laws

The rules that hold across the **whole** factory. Each names the skill that owns and enforces it;
the detail lives there, never here. Procedures do not belong in this file.

> **How this file is loaded.** Claude Code documents that a `CLAUDE.md` at a plugin root is **not**
> loaded as project context (`code.claude.com/docs/en/plugins-reference`, *Key Rules*). This file is
> therefore the canonical human-readable statement of the laws, and the **skills are what actually
> reach a session** — every law below is already enforced in its owning skill. Recorded as finding
> **F-1** in `docs/PHASE2_MIGRATION_REPORT.md`; making the laws load automatically is a Phase 3
> decision, not a migration change.

---

**L1 · The approved programme is law, and minutes are its units.**
An academic hour is whatever the programme says — never assume 60. Built teaching time equals the
allocated minutes exactly. Overflow goes to the handout; class time is fixed. → `course-factory`

**L2 · Main ILOs are copied verbatim and never edited, renumbered or improved.**
Sub-ILOs may be re-expressed, are marked `PROVISIONAL` until ratified, and are never renumbered
anywhere a trainee can see. A semantic change is proposed explicitly. → `course-factory`

**L3 · Official hours are never changed to fit scheduling,** and the factory never fabricates
attendance, delivered contact time or a compliance record. → `course-factory`

**L4 · NO SOURCE = NO MARITIME CLAIM.**
Never fill a gap from memory. A stated gap is a good answer; an invented fact is a failure however
plausible. Authority tiers are never upgraded. Check every source's edition on its own cover page.
→ every skill; markers defined by `novikontas-course-start`, fallback in `resources/org-dependencies/`

**L5 · 80/20 practical, or theory delivered as active learning.**
Where the programme's own table makes 80 % impossible, theory hours are delivered as active
learning. A theory block with no trainee activity in it is a defect. → `course-factory`

**L6 · Tablet-first, touch-first, offline.**
An 800×1280 portrait finger target first, then landscape, then the projector. Targets ≥ 44 px, no
hover-only affordance, ES5 in shared engines, nothing at class time depends on a network.
→ `course-module-ux`, `course-task-ux`

**L7 · Nothing is useless until you have grepped for what depends on it.**
Grep the id, class, label and filename across both terminals, the course tree and every generated
script before removing anything. → `course-factory`

**L8 · Explain and relocate; do not delete.**
"Why is this here?" is a report about the presentation, not proof the thing is useless. Cutting
usable material to satisfy a complaint is a worse defect than the clutter was. → `course-module-ux`

**L9 · Edit; do not regenerate.** Freeze stable artefacts and patch them. → `course-factory`

**L10 · Visible must be sufficient, not merely short** — and if a visible line refers to something,
name that something on the same line. This outranks any word budget. → `course-module-ux`

**L11 · A generated file is never hand-edited.** It carries `DO NOT HAND-EDIT` in its header and is
regenerated after any change to its input. Overrides live inside the generator.
→ `course-module-ux` (run script), `course-tablet-publisher` (registry)

**L12 · Every asset carries provenance, a licence and a visual verification**, in a metadata file
beside the file. Open and look at every image before using it.
→ *no owning skill yet — `course-visuals`, Phase 3*

**L13 · A visualisation must explain a mechanism, state change, relationship, flow, sequence or
cause/effect.** Decorative movement is not sufficient.
→ *no owning skill yet — `course-visuals`, Phase 3*

**L14 · The reference course, `source_files/`, the knowledge base and the Android application are
read-only to the factory.** → `course-tablet-publisher`

**L15 · A green exit is not proof.** Run every check, read the output, inspect the line for the
thing you changed. Report what failed as plainly as what passed. → `course-factory`

**L16 · The factory builds and reports; the owner approves, commits, publishes and installs.**
Nothing is built until the gate table is approved. Published is not installed.
→ `course-factory`, `course-tablet-publisher`

---

**L12 and L13 have no enforcing skill in this release.** They are stated here because they are
already laws of the house, and their owner (`course-visuals`) arrives in Phase 3. Until then they
depend on the operator.

Organisation-skill dependencies and their fallbacks: `resources/org-dependencies/ORG_DEPENDENCIES.md`.
