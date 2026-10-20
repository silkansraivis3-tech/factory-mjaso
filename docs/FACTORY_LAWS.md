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

**L26 · The operator's request wins. The material keeps four hard limits; the design is the person's, after one
warning** *(design part revised 2026-10-15, 2.30.0)*. Everything a colleague asks for about the material — content,
structure, emphasis, number of slides, examples, tasks, wording — is done. Four hard limits, all on the material side:
the programme and its Main ILOs · the official hours · no source, no maritime claim (a fact the operator states is a
source) · the offline tablet; hitting one: one or two plain sentences why, the closest option that works, then do it.
The design — brand colours, typeface and logo use, shell and components, layouts, animation, the recap and the
picture viewer, text size, space, the 3D share (`knowledge/design-rules.json`) — is the person's: nothing conflicts,
do it; it goes against a rule, say the rule and the risk once and ask, their way or the factory's; their way is done,
recorded in `STANDARDS.md` (`scripts/design_choices.py`), reported by every check as their choice and never changed
back. Owner: *"claude should tell person about this risk, but still after person reviews and tells that he wants his
way, plugin listens to that."* → `course-factory` (`SKILL.md`, `references/laws-in-full.md`,
`knowledge/design-rules.json`, `scripts/design_choices.py`, `retrofit/knowledge/routing.json` edit mode,
`content-lock.json`, `expert-edits.json`; the same block near the top of every skill)

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
Amended by L49 (2.26.0): ~5-minute cycles; the density counts plain theory only.
→ `course-factory` (`scripts/content_script.py`, 2.17.0)

**L37 · Every slide leaves room for its picture.** Each slide names the kind of visual, what it shows, its layout,
and who makes it - the factory, the image/video generator (context only), the sources, Novikontas (photo, film, phone
3D scan) or outside help. 40+ min of theory: something that moves, turns or can be explored.
→ `course-factory` (`knowledge/media-and-tasks.json`, `scripts/content_script.py`, 2.18.0); built by `course-visuals` (steps 8-9)

**L38 · Tasks are varied and hands-on.** Nineteen ways of answering since 2.28.0 (fourteen until then), none typing; 2+ per self-check, 3+ per module
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

**L43 · Every module in its own folder, complete, starting with a double-click.** `course\modules\M01_<title>\` holds
the presentation, the tasks, the instructor files and every asset and script it uses; nothing outside it, nothing
fetched. `START_HERE.html` opens the presentation straight away; `START_HERE_EXTENDED.html` has a button for
everything. → `course-factory` (`scripts/check_module_folder.py`, 2.19.3), `course-module-ux`, `course-tablet-publisher`

**L44 · Three places in the work folder.** `to_review\` - only what the operator checks; `modules\` - the finished
modules; `working_claude\` - everything only the factory uses, all kept (state, logs, notes, data, checkpoints).
Nothing loose. → `course-factory` (`scripts/workspace.py`, every tool, `tidy` for older courses, 2.20.0)

**L45 · The course folder is built to the classroom system's own rules.** `course\modules\` is the folder added to the
classroom: COURSE.html, `_course_shell\course_map.js`, `module01\` ... with `presentation\index.html` (slides with
`data-title`, notes in `data-cue`, task slides with `data-activity` + `data-task-href`), `tasks\`, `assessment\`; task
pages report `gb-task-done`; module checks PASSED / NOT PASSED for understanding, not an official grade. Proved by the
classroom's own importer. → `course-factory` (`knowledge/classroom-system.json`, `scripts/check_course_package.py`, 2.21.0)

**L46 · 3D where it makes sense - at most half of the presentation - at full quality, and smooth on the tablet.**
Owner, 2026-10-07: not on every slide, never at a lower quality, only where it makes sense. 3D for what has a shape, an
inside or a layout in space; at most half of a presentation's teaching slides; speed from how scenes run - one shared
renderer, scenes built and freed with their slide, no frame while nothing moves, shadows worked out once while still -
never from a lesser look; 30 frames a second with the CPU slowed 4x. → `course-factory` (`knowledge/media-and-tasks.json` three_d,
`scripts/content_script.py`, `scripts/check_course_package.py`, 2.22.0)

**L47 · A generated picture only after the person described it and said yes.** About €0.10 a picture (owner,
2026-10-14): the places are listed first, the person describes each in eight plain questions, sees the prompt, and
only their yes generates it - once; the nano-banana tools refuse without their words; the count and cost are said every
time. → `course-factory` (`scripts/picture_briefs.py`, `knowledge/media-and-tasks.json` generation_brief) and
`nano-banana` 1.2.0 (`approved_by_user`, the usage log)

**L48 · The Bloom level is measured, and the tablet lifts it.** Owner, 2026-10-15: on paper and in Google Classroom
almost every task was Remember; the tablet lets a trainee operate, find and decide. Every ILO's level is read from its
verb, every task's from how it is answered; the Stage 2 and Stage 3 pages show where the course is, every task below
its Sub-ILO, and the tablet task types that would lift it - suggestions in 2.25.0, never a stop. → `course-factory`
(`knowledge/bloom.json`, `bloom/GUIDE.md`, `scripts/bloom_map.py`, 2.25.0)

**L49 · 20 / 80 in class - the programme unchanged, every theory slide kept.** Owner, 2026-10-15: on paper the
programme stays 80/20; in class plain theory aims at a fifth of the minutes and the trainees do something for the
rest. Theory is never removed to get there - a plain slide keeps its words and gives up minutes; theory comes in
~5-minute cycles (L36 amended: 5 min and 125 words before a self-check; the words-per-minute floor counts plain
theory only). Measured on both review pages - a suggestion. Makes L5's 80 % visible. Since 2.27.0 the factory
proposes, per sub-topic, how theory is learned by doing, and the operator keeps or strikes each on the Stage 2 page;
only kept ones are built (`knowledge/active-learning.json`, `active/GUIDE.md`, `scripts/active_plan.py`). Since
2.28.0 five new tablet tasks reach the higher Bloom levels - find the fault, spot the errors, build the plan, rebuild the incident, compare (`course-task-ux` §2a). → `course-factory`
(`knowledge/theory-rules.json` split, `scripts/content_script.py`, `scripts/make_architecture_page.py`, 2.26.0)

**L50 · A fix is not a build - find, one list, one yes, change, one check.** Owner, 2026-10-15: fixes faster and
still quality; "find all free spaces in other modules" must not go through 3-4 QA reviews first. On GAS ADVANCED a
module took 1-1.5 h to build and a minor fix about 30 min, because every fix ran the build's whole process. A
correction to modules already built (one, some or all) is the **fix** mode: it reads only `fix/GUIDE.md`, the course's
`COURSE_STATE.md` and `STANDARDS.md`; finds every place in every module at once (measured at 1280 x 800 in a hidden
browser, one module at a time) as one numbered list; the operator says yes once for all of it; words change in the
content script and the built slides together (L29 kept), a part every module uses is changed once in
`working_claude\shared\` and copied into each module (L43 kept), a module with its own generator is changed in the
generator; then one check for the kind of change, run once by whoever made the fix - no QA agent after the fixer, no
untouched slide re-measured, no whole-course QA, at most 2 agents at once. A course-wide wish said once becomes a
numbered standard and is never repaired again. The full sign-off stays for builds, retrofits and handover.
→ `course-factory` (`fix/GUIDE.md`, `knowledge/fix-rules.json`, `scripts/fix.py`, `scripts/measure_slides.py`, 2.29.0)

**L51 · Every picture opens full screen, and every module closes with the same recap.** Owner, 2026-10-15: every
picture, illustration and explanatory image can be tapped to full screen and closed again; each module ends in its
module check, and before it a beautiful summary - animated boxes, the main points to take away - with the same closing
design in every module. One shared viewer, `gb_zoom.js` / `gb_zoom.css`, on every page that shows a picture (tap opens;
X, tap outside, Esc, swipe down, Back or the next slide closes; pinch, double-tap or + / − zoom; a ⤢ corner button
where the trainee answers on the picture). Full screen shows a photograph's own record under it - the part of a
drawing it shows, what is in it, whose it is (L56) - and a slide that is a photograph opens on a tap of its bare picture
area and carries the ⤢ button (operator, 2026-10-15: one viewer, L51's, with L56's explanation in it; compiled decks
load it too). One recap slide, `"recap": true` in the script, 3-6 points, straight before
the module check's task slide, built in `.slide.dark.recap` (`gb_compose.css` 15). Both are design: the person may
choose otherwise after hearing the risk (L26).
→ `course-factory` (`content_script.py`, `check_course_package.py`, `knowledge/theory-rules.json` recap),
`course-module-ux` (`assets/gb_zoom.js`, build/GUIDE.md 6a), `course-module-ui` (`gb_compose.css` 15, `design-system.json`, 2.30.0)

**L52 · As many real photographs as possible.** Owner, 2026-10-15: *"add as many real photos as possible"* - in
the presentation and in the trainee tasks. Wherever a camera can show it, the slide's picture is a real photograph,
or a small real photograph goes beside the drawing (the build sheet's `inset`); drawings and animations stay for what a
camera cannot show - insides, flows, principles. Looked for in the knowledge base, the old course and the source
files first, then free-licensed photographs on the internet, credited (title, author, source, licence, "resized");
photos still missing go on the "photos to take at Novikontas" list. Never an AI picture of equipment a trainee must
recognise (L33). → `course-factory` (`knowledge/media-and-tasks.json` floors `real_photo_*`, `scripts/content_script.py`
suggestion `v_few_photos`, `compile/` inset and credit line, 2.25.1) and `course-visuals`

**L53 · No empty space, good padding.** Owner, 2026-10-15. A picture takes the room the words leave - never a small
drawing in a large column; words are at reading size (the shared `.copy`), never a small cluster in an empty box; the
screen keeps its padding and the chrome's safe area, and nothing spills. A deck is built from the shared layouts only
(`compile/`), and passes the browser audits before it is shown: `audit_compose.js` (every screen composed, none
weak), `audit_deck.js` (no spill, no overfill), `audit_collide.js`. → `course-factory` (`compile/`) and
`course-module-ui` (`gb_compose.css` §13b, 2.25.1)
*Inside the figure too* (operator, 2026-10-15, after M01 s04: "the visual is too big, much empty space, the
information about it too small and too little, the buttons aren't clickable"). (1) A figure is drawn to the frame it is
shown in and fills it: at most half of the frame blank, no blank piece over a fifth (`audit_drawing.js` EMPTY, judged
at the figure's last step too) - crop a sparse drawing to what its steps show, or give the room to the words.
(2) The words that explain a figure are at reading size: a figure whose steps are the slide's lines sits beside them
(`two-col`), never as a large stage drawing over a row of small cards. (3) A line a step lights is the way to that
step - tap it (or Enter) and the step plays; anything that looks like a button works like one. Checked at
1280 × 800, 1024 × 768 and 1920 × 1080. → `course-visuals/kit` (`kit.js`, `kit.css`, `SPEC.md`), `course-module-ux`
(`audit_drawing.js`), `course-module-ui` (`gb_compose.css`), 2.26.3

**L54 · Every drawing whole and clean.** Owner, 2026-10-15, after the IGF pilot: an engine room poking out through
the ship's sloping stern, a cargo area through the curved bow, a fuel tank and a vent-mast top cut off at the edge, labels
printed over a deckhouse and through a box's border. (1) A part drawn inside a hull, tank, room or box stays inside its
real shape - where the hull slopes or curves, the room follows it or is clipped to it. (2) Nothing is cut off at the
drawing's frame - not the line's thickness, not a part that shows in a later step. (3) Every label has its own clear
space: 4 px on screen to any other shape, line or label, and 4 px from the edge of the box it sits in. An intentional
crossing is marked in the drawing (`data-may-cross`, `data-no-contain`, `data-may-overlap`). → `course-module-ux`
(`measure/scripts/audit_drawing.js`, run before a deck is shown; `assets/gb_fit.js`, the safety net in every compiled
deck that widens a frame a drawing still reaches past) and `course-visuals` (`review/knowledge/visual-floor.json`
`drawing_geometry`), 2.25.2

**L55 · Figures come from the figure kit; a missing part is made into the kit.** Owner, 2026-10-15, after the IGF
pilot's tank-monitoring slide shipped as four hand-drawn snapshots that swapped instead of moving: *use the kit; if
the kit has no element for what the module needs, the AI creates the element, puts it in the kit, and asks for a merge
once the module is complete.* (1) A drawn figure that shows a system, a state, a flow or a sequence is a figure-kit
spec (`NAME.kit.json`: parts and steps), never a one-off SVG; the kit draws it, moves its values between steps, fires
each alarm as its value crosses its mark, and lights the slide's lines. (2) A part the kit lacks is made to the kit's
contract in the module's own `assets/kit_parts.js` - kit helpers, course tokens, ISA-101 colour, an example spec - and
used at once. (3) Once the module is complete it is promoted into the factory's kit and a merge request goes to the
owner; in a parallel build only the orchestrator promotes, at assembly, so no two modules write the kit. Real
photographs still come first for anything a trainee must recognise (L52). → `course-visuals` (`kit/`: `kit.js`,
`kit.css`, `SPEC.md`, `PARTS.md`, `scripts/check_kit.py`, `scripts/kit_parts.py`, `GALLERY.html`), `course-factory`
(the compiler places a kit spec and ships the kit) and `course-module-ui` (`design-system.json` installs it), 2.26.0

**L56 · Every photograph carries what it shows into the viewer - unasked.** Operator, 2026-10-15, from Aigars's review
of the IGF pilot: *"we need images to be expandable, so a lightbox with maybe more explanation about the photo"*, and
*"the factory needs to make it on its own"*. The viewer is L51's `gb_zoom.js` (one viewer; the panel `gb_photo.js` of
2.27.0 is retired). (1) Every photograph's record - its `description` in `assets\img\_photo_meta.json`, written when the
photo is brought in: what is in the picture and where to look, for a trainee, never more than the picture evidences -
and its credit go onto the `<img>` (`data-about`, `data-credit`; `data-name` for an L57 thumbnail), and full screen
shows them under the picture. (2) Nobody asks for it per slide: the compiler writes them on every photograph. A photo
with no description is reported at build. (3) A picture made by an image model keeps its full record (`"generated":
true`, `"generator"`, the prompt, the operator's yes - L47) but carries no credit line and no label on screen
(operator, 2026-10-15), and L57 never places it as a thumbnail; the thing it stands in for stays on
`PHOTOS_TO_TAKE.md` until a real photo replaces it (L33). → `course-factory` (`compile/` writes the record onto every
photograph), `course-module-ux` (`gb_zoom.js` shows it), 2.27.0, 2.33.0

**L57 · A drawing of real things carries their real photographs - unasked.** Operator, 2026-10-15, looking at the
IGF pilot's "five new spaces" drawing: *"if there is an illustration like this, there would also be a real image of it,
maybe smaller, somewhere close, which you can click and see the real one"*. (1) Every drawn slide's real things - the
parts its lines name ("Tank connection space - ...") and the labels the drawing writes on itself ("vent mast") - get
their real photographs in a row under the drawing: small, numbered like the drawing's own steps, each opening full
screen with its record (L51, L56). At most four. (2) Matched by the photo's `shows` in `_photo_meta.json` - the plain names of what the picture
really shows, written when the photo is brought in; a photo with no `shows` is pointed out. A cleared photo of another
module of the course is copied in with its record (`copied_from`); one awaiting a rights review is never used. (3) A
real thing with no photo is reported at build and listed in `working_claude\PHOTOS_TO_TAKE.md` (each module's section
rewritten on every build, the operator's `## Notes` kept) - it is a photo to take at Novikontas, never a reason to
stop the build. A thing counts as real when its name ends in one of `knowledge/media-and-tasks.json` `photo_things`.
A build-sheet `"no_photo"` keeps a matched photo off a drawing it contradicts. → `course-factory` (`compile/`),
`course-module-ui` (`gb_compose.css` 16 `.photo-strip`), `course-visuals` (`_photo_meta.schema.json` `shows`), 2.27.0

**L58 · Every photograph once in the whole course.** Operator, 2026-10-15, after the same Viking Grace deck-tank photo
came up under five drawings of IGF Module 3: *"don't have duplicate images - either a different one or none, on all
modules"*. (1) A photograph is shown on one screen of the course only - as a slide's picture, an inset, a photo in a
drawing or an L57 thumbnail. The same picture copied under another name in another module is the same photograph
(the compiler compares where it came from, `url_or_origin`, else the file's bytes). (2) A thumbnail never repeats a
photograph the course already shows: it takes a different photo of that thing, or none, and the thing goes on
`PHOTOS_TO_TAKE.md` - another real photo of it lets it be shown. (3) A photograph placed by hand twice - on two slides,
or on a slide of a later module than one that already shows it - is a problem the build reports, to fix with a different
photo or none; the earlier module keeps it. A thumbnail elsewhere gives way on its module's next build, so build every
module again after photos change. → `course-factory` (`compile/`), 2.27.0

**L59 · No module before its map.** Owner, 2026-10-16, after a session building IGF Module 4 got the ILO map and the
knowledge base only by a follow-up message: *"before creating any module the AI should have already made the ILO
mapping and suggested for KNOWLEDGE_BASE to be created"*. Before any module's content is written, the course has its
ILO map (`working_claude/ilo_map.json`), approved on the Stage 2 page, and a recorded knowledge-base decision. When
there is no knowledge base, the factory suggests making one, unasked - what it is, from which files, how (the Course
Source Processor; the factory has no builder) and what the course loses - and records yes / built / declined with the
operator's reason, once. Every Sub-ILO is taught on a slide and checked by a question, and every fact traces to a
listed source. A script approved before the law keeps its approval; its gaps are reported. → `course-factory`
(`scripts/ilo_map.py`, `scripts/course_gate.py`, `kb/scripts/kb_tool.py`, `script/GUIDE.md` §0), 2.42.0

**L60 · At least one 3D scene in every module where the subject allows it - strongly recommended.** Aleksis,
2026-10-19, after the M01 benchmark built a planned 3D slide as a flat figure without a word: *"it should be like it is
very recommended to build a 3d model at least once where you can in a module"*. A module whose script plans no 3D still
gets one where a slide's lesson is a shape, an inside or a layout in space: `--init-build` picks the best slide unasked
(one the script plans as 3D first, else the best fit) and writes its starter scene entry, built like IGF M03's
`m03_station3d.js`. A module built with no 3D scene is said loud in the build and in its own card on the review page -
the best candidate and why. A recommendation, never a block (2.18.1): the operator may decline it with their reason
(`"declined_3d"` at the top of the build sheet), and a declined scene is not proposed again. A slide the script plans as
3D that is given a 2D figure stays a must-fix until its own `"declined_3d"` holds a reason. L46 is unchanged - at most
half the teaching slides, never instead of a real photograph, the speed and tap rules of the compile GUIDE 2b.
→ `course-factory` (`scripts/content_script.py` `best_3d`, `build_findings`; `compile/scripts/compile_module.py`), 2.49.7

**L61 · Physical equipment is drawn as it looks on board.** Aleksis, 2026-10-20, approving a plain-vs-realistic mock-up of
the figure kit: *"yes we like this new kit styling"*, then *"also do the Parts added from courses"* and *"make the ship look
realistic aswell, look at real images of it"*. (1) Every kit part that is a physical thing - a tank, a pipe, a valve, a
pump, an exchanger, an engine, a vent, a hose, a coupling, a ship - is drawn in its material (cladding, brushed
stainless, cast or painted metal, rubber, a ship's painted plating), with light and shade, and with the real features a
trainee recognises on board: flanges at its joints, saddles, a dome, a bonnet and what works it (an actuator on an
automatic valve, a handwheel on a manual one), a bedplate and a turbocharger, a superstructure's windows. (2) A screen
(panel, gauge, readout, alarm log) stays a calm ISA-101 HMI, and a diagram (a zone, a chart, a cloud) stays a diagram.
(3) The teaching state stays readable at a glance - the fluid's front, open or shut (the ISA bow-tie stays on the valve
as a plate), running, alarms - and amber and red stay reserved for alarm and trip: materials are neutral greys and
blues, copper only for a heating coil. (4) It is the kit's own look, on in every deck - no spec option, no per-slide ask.
A new part declares its `look` (`equipment`, `screen` or `diagram`) and an equipment part draws its bodies with
`KIT.h.body` / `KIT.h.equip` and the kit's materials; `check_kit.py` refuses one that does not. →
`course-visuals` (`kit/kit.js` materials, `KIT.h.body`, `equip`, `flange`; `kit/kit.css` `--mat-*`; `SPEC.md` "Rules of
the look"; `PARTS.md`; `scripts/check_kit.py`), `course-module-ux` (`audit_drawing.js` judges one piece of equipment as
one object, `data-kit-body`), 2.52.0

**All sixty-one laws name an enforcing skill.** L12 and L13 gained theirs in Phase 3, when
`course-visuals` was built; L26–L61 are enforced first through `course-factory/SKILL.md`'s
"Owner decisions in force" block, and each is built out in the step named beside it.

Organisation-skill dependencies and their fallbacks:
`plugin/skills/course-factory/org/ORG_DEPENDENCIES.md`.
