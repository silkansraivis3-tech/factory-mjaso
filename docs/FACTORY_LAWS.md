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
→ every skill; markers defined by `novikontas-course-start`, fallback in `plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`

**L5 · 80 % of class minutes learner-active; theory delivered as active learning.**
The 80 % is Track B — minutes where the trainee is doing, deciding or producing something — not
the programme's practical share, which is Track A and is never changed. Where the programme
allocates little practical time, the theory hours are delivered as active learning. A theory
block with no trainee activity in it is a defect. Theory is never removed; it is delivered as
activity — self-check, explain-then-reveal (no typing), predict-then-reveal, worked example then own
attempt (owner, 2026-09-30). → `course-factory`

**L6 · Tablet-first, touch-first, offline.**
An 800×1280 portrait finger target first, then landscape, then the projector. Targets ≥ 44 px, no
hover-only affordance, ES5 in shared engines, nothing at class time depends on a network.
→ `course-module-ux`, `course-task-ux`

**L7 · Nothing is useless until you have grepped for what depends on it.**
Grep the id, class, label and filename across both terminals, the course tree and every generated
script before removing anything. → `course-factory`

**L8 · Explain and relocate; do not delete.**
"Why is this here?" is a report about the presentation, not proof the thing is useless. Cutting
usable material to satisfy a complaint is a worse defect than the clutter was. This is for a
question or a complaint; when the operator *tells* the factory to remove something, it is removed
(L26), after L7's grep. → `course-module-ux`

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
classified on quality, never on validity. The operator's request in chat is the explicit
authorisation (L26). → `course-factory` (`retrofit/`)

**L19 · COURSE_LANGUAGE is declared, and the operator's language is not it.** *(Owner, 2026-09-30: every
Novikontas course is in English - COURSE_LANGUAGE is English and is never asked.)*
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

**L23 · A topic screen leads with the thing that shows it.**
Not "every screen has a picture" - a definition, an exact limit or a quoted regulation is carried
better by text, and a visual added to fill space is still the defect L12 rejects. The law is about
ORDER, in two senses. In the reading order: the figure is above the prose, not appended under the
paragraph that already said it. And in the build order: for a topic screen the visual is looked for
FIRST - the source files and the knowledge base, then the internet for a real photograph of the
actual equipment, then authored, and only then generated. A screen that honestly needs no figure
says which reason applies; a silent exemption is the finding, because it is indistinguishable from
nobody having looked.

When the model building the module cannot produce the image, the module is finished as far as it
goes and the request leaves with it: `write_visual_handoff.py` writes one paste-ready file naming
what to find, what to generate and exactly where each file belongs. Where the environment allows it,
that work is spawned on the agent that owns it - `nano-banana:image-director` to generate,
`course-factory:visual-sourcer` to find a real one - rather than waiting for a human. A module never stops because one picture is missing.
→ `course-visuals` (`scripts/check_visual_first.py`, `knowledge/visual-first-rules.json`)

---

**L24 · Where the expert has already changed something, that change is content.**
L18 says the existing delivery implementation is not preserved by default. That is right for
material nobody has touched since it was generated and exactly wrong for a screen a maritime
expert went into and changed on purpose — which is the most expensive information in a module,
because it is the one place somebody who actually sails ships disagreed with what was produced,
and they almost never write down why. The difference between the two laws is not what the code
looks like but **who last touched it**, so the first question of a retrofit becomes "which parts
of this are somebody's decision", asked before anything is rewritten. It is answered from
evidence, never by judging the code: a marker the expert left, the factory's own build record, a
commit the factory did not author — and if none of those exist, **ask**. "I cannot prove it was
touched" is never "it was untouched". A protected region is locked content: restyle it, never
rewrite it, and where it breaks another law name the law and propose the fix rather than applying
it. An expert who finds their change quietly corrected stops making changes. A protected region
is protected from the factory, never from the operator: when they ask for a change there, it is made
(L26).
→ `course-factory` (`retrofit/scripts/detect_expert_edits.py`, `retrofit/knowledge/expert-edits.json`)

---

*(2.19.1, owner: every reply to the operator has three parts - Done · Check now · Next - as short points in
everyday words, for someone who knows nothing about IT; maritime terms stay professional.)*

**L25 · The person reading this does not work in IT.**
Every message that leaves this factory is read by a maritime professional with no IT background.
`FAIL check_visual_first.py module.html:412 missing lead figure` is not a report to them, it is a
wall: they cannot act on it, so they either ignore it or come and ask, and both are the factory
failing to finish its own job. **A finding nobody can act on is the same as a finding nobody
made.** Every problem message carries five things — what is wrong, in the words of the course;
where it is, as a full path plus the human landmark; how to see it, in literal steps; what to do,
with an offer to do it; and what they will see when it is right. This is not dumbing down: the
maritime content stays exactly as technical as it is, and what changes is the language about
computers and this tool. A chief officer knows what an inert gas generator is and does not know
what a stylesheet is.
→ `course-factory` (`scripts/check_plain_language.py`, `knowledge/plain-language.json`)

---

## Phase 5 — the owner's decision record (2026-09-30)

**Where any older rule disagrees with one of these, this one wins**, from 2.12.0 on, before the step
that builds each one out has landed. The full text of each is in
`plugin/skills/course-factory/references/laws-in-full.md` — inside the plugin, because this `docs/`
folder is not installed with it.

**L26 · The operator's request wins, and "the style" means the brand system only.** Fixed: brand
colours, typography, logo use, and the shell, tokens, components, navigation and tablet system.
Everything else a colleague asks for — content, structure, emphasis, number of slides, examples,
visuals, tasks, wording — is done, never refused as "not in the style". Five hard limits only: the
brand · the programme and its Main ILOs · the official hours · no source, no maritime claim (a fact
the operator states is a source) · the offline tablet. Hitting one: one or two plain sentences why,
the closest option that works, then do it. → `course-factory` (`SKILL.md`, `retrofit/knowledge/routing.json`
edit mode, `content-lock.json`, `expert-edits.json`)

**L27 · Three test levels, and only the final assessment is graded.** Self-check in the presentation
and the module check at the end of every module are **ungraded**; the final assessment is the only
graded test. *(2.17.0: all three on the trainee tablet, each opened by the instructor (L35); self-checks
and module checks show the trainee their own score, which does not count.)* One task per screen, Next → Next. The module check still waits for the instructor's
unlock; the instructor sees done / not done and the result as information — never pass/fail, never
red. → `course-task-ux` (built out in step 6)

**L28 · Who the course is for, and what the school has.** `NEW_ENTRANT` or `EXPERIENCED`, declared at
intake, changes the build: new entrants get more explanation, more screens, more worked examples;
experienced get shorter theory anchored in real incidents and more scenario tasks. The course
language stays fully professional either way. Every instrument and simulator in the IMO model course
is assumed available. → `course-factory` (steps 2, 7)

**L29 · The words are approved before the HTML.** A word-for-word content script per module — every
slide's exact text, its planned visual, instructor notes, every question with answer and feedback —
approved by the operator before any HTML; the built slides then say exactly that. Facts the operator
stated are listed once per module in that review, marked operator-stated. The operator's copy is a
Word file (typing and comments both read; tracked changes read as accepted); every correction is shown
as a plain list and applied only after they confirm; tasks appear in screen order, one per screen.
→ `course-factory` (`script/GUIDE.md`, `scripts/content_script.py`, `check_script_match.py`, 2.16.0)

**L30 · Module 1 is a pilot.** Built by five roles and approved before any other module is built;
then the rest may run in parallel, each with its own script and review STOP. → `course-factory`
`orchestration/` (step 10)

**L31 · Ask like a colleague, not like a form.** No "needs SME review" spam. Real expert questions are
batched as one pop-up with options at the next STOP, then work continues. Honesty markers live in
`factory-notes.md`, never on a slide, and never stop the work. → `course-factory`

**L32 · The factory remembers.** `COURSE_STATE.md` at the end of every stage; every operator
correction in `FEEDBACK_LOG.md`; a pattern file offered when the operator is happy — shown to them in
plain language and saved only on their approval, naming the course, course type and who made it;
guidance for later courses, never law, never above the operator's request. → `course-factory`
(`scripts/course_memory.py`, 2.14.0)

**L33 · Pictures: find first, keep what teaches, never invent what a trainee must recognise.**
KB → old course → source files → internet → authored → generated. Legit old schematics are kept.
Textbook figures are redrawn technically identical, credited "after <book>" and listed for a licence
check. Equipment a trainee must recognise is never an AI image: an accurate schematic, and the
"photos to take at Novikontas" list. ICS/SIGTTO "not cleared" stays out. → `course-visuals` (step 8)
*(Revised 2.19.0, owner: every picture in the knowledge base and the old course is usable as it is - credited where
known and listed, no longer redrawn or held back; what is missing is searched on the internet and downloaded, the list
confirmed once per module. Equipment a trainee must recognise is still never an AI image.)*

**L34 · One module per programme topic.** Every topic of the programme's topic/hours table is its own
module, in the programme's order, with its own hours - GAS BASIC: 22 teaching modules. The final-assessment
topic is the last module and the assessment only. Never merged, never split. Academic hour: the
programme's; 40 min at Novikontas when it is silent. Replaces `hours/GUIDE.md` "combine topics freely".
→ `course-factory` (`scripts/make_architecture_page.py`, 2.17.0)

**L35 · Two tablets.** Slides on the instructor tablet, mirrored to the classroom screen; tasks only on the
trainee tablet. At task time the slide only announces the task and the instructor presses OPEN TASK; the
task opens on every trainee tablet by itself. No task list, no browsing, no "all tasks" / "back to
tasks". The trainee sees their own score on self-checks and module checks. Supersedes `course-task-ux`'s
trainee task list. → `course-factory` (`scripts/content_script.py`, 2.17.0); the app change list in step 6

**L36 · Enough theory before any task.** A slide carries the teaching; the notes carry the explanation;
the words fill the minutes; a self-check only after a block of new theory; every answer taught before
its task opens. Floors in `course-factory/knowledge/theory-rules.json`, checked on the content script.
→ `course-factory` (`scripts/content_script.py`, 2.17.0)

**L37 · Every slide leaves room for its picture.** Each slide names the kind of visual, what it shows, its layout,
and who makes it - the factory, the image/video generator (context only), the sources, Novikontas (photo, film, phone
3D scan) or outside help. 40+ min of theory: something that moves, turns or can be explored.
→ `course-factory` (`knowledge/media-and-tasks.json`, `scripts/content_script.py`, 2.18.0); built by `course-visuals` (steps 8-9)

**L38 · Tasks are varied and hands-on.** Fourteen ways of answering, none typing; 2+ per self-check, 3+ per module
check, "choose one" at most 40 %, a hands-on question in every module. Widens `course-task-ux` §2.
→ `course-factory` (`knowledge/media-and-tasks.json`, `scripts/content_script.py`, 2.18.0); built by `course-task-ux` (step 6)
*(2.18.1: L37 has no quota - pictures, animation and realistic 3D wherever they show the theory; the picture floors are
suggestions. Instructor notes are short points in their own .md file for the instructor's panel.)*

**L39 · Who tests where.** Every file is made ready for the tablet system; a colleague gets only the HTML, to check in
their own browser; the real-tablet test - by touch, every task type, the results the app records - is the owner's, at
the end. → `course-factory` (build, Phase 5 steps 6-10), `course-tablet-publisher`

**L40 · The factory works in `course\`, beside the course material.** The folder given is the master folder; its
source files, knowledge base and old course are read only; everything the factory makes goes into `course\` next to
them. → `course-factory` (`scripts/workspace.py`, every tool, 2.19.0)

**L41 · The old course is the foundation.** Read whole at intake; every module says what it keeps, modernises and
makes digital, and adds. → `course-factory` (`scripts/old_course.py`, `scripts/make_architecture_page.py`, 2.19.0)

---

**L42 · Trainee-tablet tasks: modern, exciting, usable with zero tablet experience.** A first *try the tablet* screen,
tap and drag only (drag also tap-then-tap), a once-only animated gesture hint, controls of 56 px and more, instant
feedback, real equipment in 3D and working panels, forgiving, offline, proved by a novice walkthrough and the owner's
tablet test. → `course-task-ux` (§0, 2.19.2; built in step 6)

**All forty-two laws name an enforcing skill.** L12 and L13 gained theirs in Phase 3, when
`course-visuals` was built; L26–L42 are enforced first through `course-factory/SKILL.md`'s
"Owner decisions in force" block, and each is built out in the step named beside it.

Organisation-skill dependencies and their fallbacks:
`plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`.
