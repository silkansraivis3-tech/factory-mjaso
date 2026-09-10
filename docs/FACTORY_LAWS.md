# Factory laws

The rules that hold across the **whole** Course Factory. Each names the skill that owns and
enforces it; the detail lives there, never here.

> **This file is documentation, not enforcement — and that is deliberate.**
>
> It used to live at `plugin/CLAUDE.md`. Claude Code does not load a plugin-root `CLAUDE.md` as
> project context, and `claude plugin validate --strict` fails on one that exists
> (finding **F-1**, confirmed by the official validator on 2026-09-10). A file that looks
> authoritative and is never read is exactly the class of defect this project keeps recording, so
> in Phase 3 it was moved here and the two laws that had no enforcing skill were given one.
>
> **Every law below is enforced by a skill that does load.** This page exists so a human can read
> the whole set on one screen. Changing a law here changes nothing; change it in the owning skill.

---

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
beside the file. Open and look at every image before using it. Unclear rights are
`RIGHTS_REVIEW_REQUIRED` and block shipping. → `course-visuals`

**L13 · A visualisation must explain a mechanism, state change, relationship, flow, sequence or
cause/effect.** Decorative movement is not sufficient, and the first question is always what the
learner must understand — never what visual goes here. → `course-visuals`

**L14 · The reference course, `source_files/`, the knowledge base and the Android application are
read-only to the factory.** → `course-tablet-publisher`

**L15 · A green exit is not proof.** Run every check, read the output, inspect the line for the
thing you changed. Report what failed as plainly as what passed. → `course-factory`

**L16 · The factory builds and reports; the owner approves, commits, publishes and installs.**
Nothing is built until the gate table is approved. Published is not installed.
→ `course-factory`, `course-tablet-publisher`

---

**All sixteen laws now have an enforcing skill.** L12 and L13 gained theirs in Phase 3, when
`course-visuals` was built; before that they depended on the operator remembering them.

Organisation-skill dependencies and their fallbacks:
`plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`.
