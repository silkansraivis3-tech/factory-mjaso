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

**L17 · Every screen must look intentionally composed.**
A screen is not finished because its elements fit, nothing overflows, the contrast passes and a
large container occupies most of the viewport. **A big empty box is not a composition.** Meaningful
content — headings, copy, diagrams, photographs, controls — must deliberately use the screen it is
given. A small cluster of text in one corner of an otherwise purposeless screen is a design defect,
however green the checks are.

Sparse is allowed when the sparsity is the composition and is visually strong: one statement, one
question, one dominant visual, one photograph, one activity code centred. Sparse never means
"a huddle top-left". Choosing a named composition from `gb_compose.css` counts as declaring intent;
`data-compose="sparse"` declares it for an ordinary flow screen.

Measured on **meaningful content**, never on container rectangles: ink share, horizontal and
vertical balance, content centroid, dead halves, and whether a teaching visual is large enough to
read from the back of a room. A warning here is a call for human review, not an automatic failure.
→ `course-module-ui` (the vocabulary), `course-module-ux` (`measure/scripts/audit_compose.js`)

**L18 · Content is locked. The delivery implementation is not.**
**Preserve the course content; do not preserve the existing delivery implementation by default.**
Locked, needing explicit authorisation: technical meaning, programme requirements, ILOs, official
hours, assessment intent, intended practical exercises, course terminology, source-supported facts,
COURSE_LANGUAGE. Free, redesigned on the evidence without asking: screen count, screen order, HTML,
layouts, density, progressive disclosure, visual and animation implementation, interactive
mechanics, task presentation, navigation, CSS/JS, hierarchy, composition.

An existing visual is *evidence of a teaching decision*: preserve the decision, rebuild the
implementation. "The HTML works" is not an argument for keeping it, and a module's delivery is
classified on quality, never on validity. → `course-factory` (`retrofit/`)

**L19 · COURSE_LANGUAGE is declared, and the operator's language is not it.**
Mandatory in every mode. Course-facing output — slides, tasks, handout, assessment, feedback,
instructor cues, practical cards, START_HERE, run script — stays in COURSE_LANGUAGE unless
translation is explicitly requested. The chat report, companion file, comments and validator output
follow the operator. A Latvian request to redesign an English module produces a Latvian report and
an English module. → `course-factory` (`retrofit/scripts/check_language.py`)

**L20 · A figure that claims to teach a dynamic idea is proven to be alive, and a probe
that cannot see is never read as a verdict.**
Every teaching figure must be one of three things, and the third is a defect:
`MOVES` (it animates on its own), `RESPONDS` (it changes when its own controls are used), or
`STATIC` (it could have been a PNG). A series/parallel toggle should *not* animate, so
"does it animate" is the wrong question; "is this drawing alive at all" is the right one.

The second half of the law is the expensive half. A hidden page suspends
`requestAnimationFrame` completely, and a motion probe run against one measures zero
movement and reports it as a property of the course. That cost an afternoon on the ETPA4
pilot: the deck's hook contract was re-read, the engine was changed and the course was
rewired, and the figure had been correct the whole time. A probe now states the
scheduler it measured under, pumps frames when the page is hidden, and never returns a
bare "does not move".
→ `course-visuals` (`scripts/verify_figures.js`, `GBVerifyFigures.motion()`)

**L21 · The production Android application is a publish target, not a workspace.**
Without explicit human approval, `AndroidStudioProjects/NOVIKONTASTraining` is READ ONLY.

A course lives in the colleague's own folder and is reviewed there, in the normal default
browser — no tablet, no Android Studio, no terminal, no server. It reaches the application
only after a person has said so about that named course and version, in their own words:
*"Approved. Publish this course to the NOVIKONTAS training app."*

"Make this module better" is course work, and so is every other improvement request; none of
them may write a byte into the Android project. Approval given for a previous version is not
approval for this one. Enforced rather than stated: `publish.py --publish` refuses without
`--approved-by` before it even opens the platform file, and the approver is recorded in the
commit — the repository should say who approved a course, not only who ran a script.
→ `course-tablet-publisher` (`references/preview-and-approval.md`, `scripts/preview.py`)

**L22 · A slide is not an internal document.**
Four rules, from a maritime subject-matter reviewer reading a finished module. None is
about one course; each is about the difference between a file the Training Centre keeps
and a page a trainee reads.

- **Internal shorthand never reaches a slide.** A Training Centre abbreviation printed on
  a screen implies it is an IMO title or an industry term. It is neither. Write the course
  out in full.
- **The title slide carries no version control.** No revision number, no approval status,
  no internal authority designation. It is the first thing a room sees and it should look
  like training material.
- **An IMO model course is never cited as a source.** It is a training REQUIREMENT and a
  guide to what a course must cover - not a source of factual information. A slide reading
  "Source: IMO Model Course 1.01" tells the room a syllabus is where the fact came from.
  Cite the publication the fact actually came from, or cite nothing.
- **Figures too.** "Figure: IMO Model Course 1.01, 1.2" is the same error wearing a
  caption. Do not credit a model course for a drawing.

And one the factory owes itself: **its own honesty markers never appear on a slide.**
PLACEHOLDER, PROVISIONAL, TBD, [VERIFY: …] are a message to the owner and belong in
`factory-notes.md`, which exists for exactly that. No second file is needed.

An instructor's own plan or run sheet may cite a model course - that is how an instructor
knows why a topic is in the course - so there it is reported and never failed.
→ `course-factory` (`scripts/check_slide_text.py`, `knowledge/slide-text-rules.json`)

---

**All twenty-two laws now have an enforcing skill.** L12 and L13 gained theirs in Phase 3, when
`course-visuals` was built; before that they depended on the operator remembering them.

Organisation-skill dependencies and their fallbacks:
`plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`.
