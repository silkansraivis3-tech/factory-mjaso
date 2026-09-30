# The course-factory laws, in full

*Moved here word for word from `course-factory/SKILL.md` in 2.11.0 (Phase 5, step 11) so the
skill file every session reads stays light. Nothing was deleted or reworded. SKILL.md keeps each law's operative rule; read this when a law is in question, when an operator's request seems to collide with one, or before changing one.*

---

## The nine laws

These are not preferences. Each one is here because breaking it cost real rework — the first four
on GAS BASIC, the last two on the first two real pilots. Numbered as in `docs/FACTORY_LAWS.md`,
the one numbering the whole factory uses.

### L1 · The approved programme is law, and minutes are the law's units

`hours/knowledge/hours-rules.json` is the authority — read it, do not restate it. The short form:

- An academic hour is whatever the programme says it is (GAS BASIC: **40 min**). Never assume 60.
- Every module's built teaching time must equal its allocated minutes **exactly**.
- Anything that will not fit becomes **self-study in the handout**. The handout is the overflow
  valve; class time is fixed. *(Owner's ruling, 2026-09-07.)*
- Run `hours/scripts/check_hours.py` before believing any plan. It exits non-zero when the sum
  is wrong, and it is the gate.

**What this law is for.** GAS BASIC was built to 2175 minutes against an accredited 1640 — a
33 % overrun discovered only after all eight modules existed, because nothing counted minutes
until someone thought to. The contract that orders the whole course factory
(`COURSE_START.json`) has **no hours field at all**. This lane adds one.

### L2 · Main ILOs are untouchable

Main ILOs and the approved study programme are copied **verbatim** and never edited, renumbered
or "improved". Sub-ILOs **may** be re-expressed to make a topic digital or practical — that is
the point of the exercise — but:

- a re-expressed Sub-ILO is marked `PROVISIONAL` until the owner ratifies it, and
- it is **never renumbered in anything a trainee sees**.

IMO model courses are **guidance**; the approved programme **governs**. Where they disagree, the
programme wins and the model course is cited as support, never as authority.

### L5 · Two tracks, and only one of them is yours

This is one rule that reads like two numbers, and the ETPB3 pilot got it wrong by treating them
as the same number. Keep them apart.

**Track A — the allocation.** The approved programme says how many academic hours are theory and
how many are practice. That is external, auditable and **not editable**. Your job is that the
module as *built* claims those same minutes against those same buckets: a module claiming 20
practice hours puts 800 minutes of trainee practice in front of the room. ETPB3 built 650 theory
/ 630 practice against an allocated 480 / 800 and nothing caught it, because `check_hours.py`
only compares the **total**. A total-only check cannot see a bucket swap. Declare the bucket per
block with `data-track` and run `check_balance.py`.

**Track B — the delivery modality.** Of the minutes in front of the room, how many have the
trainee *doing, deciding, producing or saying* something, and how many have them receiving? This
is a **design metric**. It changes nothing in Track A — a theory-allocated minute delivered as an
activity is still a theory minute. Declare it per block with `data-active`.

**The 80 % target belongs to Track B.** Aim for 80 % of class minutes learner-active. Where the
programme makes the *practical* share small — GAS BASIC allocates 8 practical hours of 43 — the
answer is not to give up but to make the theory hours active:

> the theory hours are **delivered as active learning** — a tablet task inside the theory block,
> not a longer lecture.

Mandatory, not optional. A theory block with no trainee activity in it is a defect.

Record both figures in the companion file with the reason for any shortfall. **Do not reach the
target by renaming screens.** `check_balance.py` rejects the three ways people try: an active
count above the block's own minutes, a practice block whose room is receiving for most of it, and
a theory block claiming 100 % active — somebody has to set the task.

### L7 · Nothing is useless until you have grepped for what depends on it

Before removing any control, label, field or file: grep its id, class, label and filename across
**both terminals, the course tree and every generated script**. On GAS BASIC, three of four
"useless" findings were load-bearing — timer buttons the instructor run script tells the
instructor to press, print buttons on hand-out documents, and hrefless `<span id="gb-home">`
elements that are how a page declares it has no way back. Unused today is not useless: data a
planned system will read is not dead.

### L18 · Content is locked. The delivery implementation is not.

> **PRESERVE THE COURSE CONTENT. DO NOT PRESERVE THE EXISTING DELIVERY IMPLEMENTATION BY DEFAULT.**

`retrofit/knowledge/content-lock.json` is the authority — read it, do not restate it.

**Locked**, needing explicit authorisation: technical meaning, programme requirements, ILOs and
Sub-ILOs, official hours, assessment intent, intended practical exercises, course terminology,
source-supported facts, COURSE_LANGUAGE.

**Free**, redesign on the evidence without asking: screen count, screen order, HTML structure,
layouts, card arrangements, density, progressive disclosure, visual implementation, animation,
interactive mechanics, task presentation, navigation, CSS/JS, hierarchy, composition.

**What this law is for.** A colleague asked for an existing module to be brought up to GAS BASIC
quality and got back a technically correct retrofit that still felt weaker than GAS BASIC — because
Claude treated the existing HTML as something to preserve. Conservatism looks like diligence.
Keeping a layout feels safer than replacing it, every single decision to keep something is
defensible, and the sum of them is a module that passes every check and is not the product. **The
existing module is source material plus learning intent, not the presentation template**, and "the
HTML works" is not an argument for keeping it.

An existing visual is *evidence of a teaching decision*: preserve the decision, rebuild the
implementation. The star/delta figure's claim — the supply never moves, only the bridges change —
survives; its small SVG does not have to.

### L24 · Where the expert has already changed something, that change is content

> **BRING IT UP TO STANDARD. NEVER OVERWRITE IT, NEVER TIDY IT AWAY, NEVER DECIDE IT WAS A
> MISTAKE.**

`retrofit/knowledge/expert-edits.json` is the authority; `retrofit/scripts/detect_expert_edits.py`
answers the question. This is the exception L18 needs, and it points the other way: L18 is
right about material nobody has touched since it was generated, and exactly wrong about a screen a
maritime expert went into and changed on purpose.

An expert edit is the most expensive information in a module. It is the one place where somebody
who actually sails ships disagreed with what was produced, and they almost never write down why.
Rebuilding over it destroys the disagreement silently, and the expert finds out in front of a
class.

**The difference between the two laws is not what the code looks like — it is who last touched
it.** So the first question of a retrofit is no longer "how good is this", it is "which parts of
this are somebody's decision", and it is asked before anything is rewritten. Good expert edits
often look untidy and generated filler often looks deliberate, so that judgement is never made by
reading the code. It is made from evidence, in this order: a marker the expert left (`data-sme`,
`<!-- SME: … -->`, a file in `_sme/`) · the factory's own build record (`_factory/build.json`,
whose hash no longer matches) · a commit the factory did not author · **and if none of those
exist, ask.** Never read "I cannot prove it was touched" as "it was untouched".

A protected region is **locked content**, the same tier as a technical fact. Restyle it — tokens,
typography, the layout shell, accessibility, broken markup. Do not rewrite the words, reorder the
points, change a value, delete a screen they added or restore a screen they deleted.

**Where a protected region breaks another factory law, name the law and propose the fix in the
report. Do not apply it.** An expert who finds their change quietly corrected stops making
changes, and then the course has no maritime judgement in it at all.

Every run writes the record at the end, after verification passes. That is what makes the
question disappear for good: the first retrofit asks it once, and no retrofit after that ever
needs to.

### L21 · The production Android application is a publish target, not a workspace

> **Without explicit human approval, the Android repository is READ ONLY.**

A course lives in the colleague's own folder. It is reviewed there, in the normal browser,
with no tablet and no Android Studio — `course-tablet-publisher`'s `preview.py` writes a
`REVIEW.html` beside it and opens it. A course reaches
`AndroidStudioProjects/NOVIKONTASTraining` only after a person has said so about that named
course, in their own words: *"Approved. Publish this course to the NOVIKONTAS training app."*

**"Make this module better" is course work.** So is "fix the tasks", "redesign module 1" and
every other improvement request. None of them may write a byte into the Android project, and
an approval given for a previous version is not approval for this one.

Enforced, not merely stated: `publish.py --publish` refuses without `--approved-by`, before
it opens the platform file, and records the approver in the commit.
→ `course-tablet-publisher` (`references/preview-and-approval.md`)

### L19 · COURSE_LANGUAGE is declared, and the operator's language is not it

Mandatory in **plan** and **retrofit** alike. Detect it from the authoritative course-facing
material, state it back in one line, and lock it.

Course-facing — slides, tasks, handout, assessment, feedback, instructor cues, practical cards,
START_HERE, the run script — stays in COURSE_LANGUAGE unless translation is **explicitly**
requested. The chat report, `factory-notes.md`, code comments and validator output follow the
operator.

A Latvian operator asking, in Latvian, to redesign an English module gets a Latvian report and an
English module. Translating an accredited artefact because the request arrived in another language
destroys it, and it happens one screen at a time. `retrofit/scripts/check_language.py` is the
drift check.

---

### L25 · The person reading this does not work in IT

> **EVERY MESSAGE THAT LEAVES THIS FACTORY IS READ BY A MARITIME PROFESSIONAL WITH NO IT
> BACKGROUND.**

`knowledge/plain-language.json` is the authority; `scripts/check_plain_language.py` enforces it.

A line reading `FAIL check_visual_first.py module.html:412 missing lead figure` is not a report to
them, it is a wall. They cannot act on it, so they either ignore it or come and ask — and both of
those are the factory failing to finish its own job. **A finding nobody can act on is the same as
a finding nobody made.**

Every problem message carries five things, and all five:

| | |
|---|---|
| **What is wrong** | one sentence, in the words of the course, not of the software |
| **Where it is** | the full path from the drive letter, plus the human landmark — which module, which slide, which heading |
| **How to see it** | the literal steps. Double-click what, opens in what, what appears |
| **What to do** | the fix in steps — and if the factory can do it, offer: *"tell me to fix it and I will"* |
| **How they know it worked** | what they will see afterwards. Never *"run the check again"* as the only proof |

**This is not dumbing down.** The maritime content stays exactly as technical as it is — tank
types, flammable limits, the IGC Code. What changes is the language about *computers and this
tool*. A chief officer knows what an inert gas generator is and does not know what a stylesheet
is, and nothing about the first fact excuses the second word.

Most fixes belong to the factory, not to them. **Offer to do the work before explaining how they
could.**

---

## Phase 5 — the owner's decision record (L26–L33, 2.12.0; L34–L36, 2.17.0)

Decided by the owner on 2026-09-30. **Where any older rule in this factory disagrees with one of
these, this one wins** — and that holds from 2.12.0, before the step that builds each of them out
has landed. The one-line operative form of each is in `SKILL.md`; this is the full text.

**L26 · The operator's request wins, and "the style" means the brand system only.**
Fixed: the Novikontas brand — its colours, typography and logo use — and the product it is built
into: the shell, the tokens, the components, the navigation, the tablet system. Nothing else is
"the style". Everything a colleague asks for about content, structure, emphasis, the number of
slides, examples, visuals, tasks or wording is **done** — never refused, never watered down, never
quietly left out because it is "not in the style".

The operator's request in chat **is** the explicit authorisation L18 asks for. It reaches regions an
expert edited, too: L24 protects an expert's change from the *factory*, not from the operator.

Five limits are hard, and only five:

1. the Novikontas brand;
2. the approved programme and its Main ILOs, copied verbatim (L1, L2);
3. the official hours (L1, L3);
4. no source, no maritime claim (L4) — a fact the operator states **is** a source: use it, record
   it in `factory-notes.md` as theirs with the date, and list it in the module's content-script
   review (L29);
5. the offline tablet (L6) — everything bundled, nothing fetched at class time.

When a request truly hits one of them, say why in one or two plain sentences, offer the closest
option that works, and do that. *"The Main ILO has to stay word for word, so I added your wording
as a Sub-ILO under it"* — not a refusal, and not an essay.

Every other rule in this factory written as "never", "must not" or "not negotiable" is a rule for
the factory's **own** choices — what it does when nobody has asked for anything. None of them is a
reason to refuse the operator. Where one would make the result worse for what was asked, say so in
one line and do what was asked.

**L27 · Three test levels, all on the tablet, and only the final assessment is graded.**

*Revised by the owner, 2026-09-30 (2.17.0): the tests are on the **trainee tablet only**, never inside the
slides (L35); a self-check **does** show the trainee a score — "it's for himself"; the module check does too.
Neither counts. The table below is the 2.12.0 text; where it says otherwise, this note wins.*

| Level | Where | Graded |
|---|---|---|
| Self-check | inside the presentation, after key concepts *(2.17.0: on the trainee tablet, opened by the instructor after the theory it tests — L35, L36)* | no |
| Module check | the end of every module | **no** — a self-check that the module was understood |
| Final assessment | the end of the course | **yes** — the only graded test |

One task per screen, large touch targets, Next → Next, clear feedback on every self-check; no score
shown on an ungraded check unless the score itself helps the trainee learn. *(2.17.0, owner: it does —
every self-check and module check ends on the trainee's own score.)* The ungraded module
check **still waits for the instructor's unlock**. The instructor's screen shows *done / not done*
and the result as information — never pass or fail, never red. The tablet app's own web files
colour a check red today; the factory writes the exact change list and the owner applies it (L21).
→ built out in `course-task-ux` (Phase 5 step 6).

**L28 · Who the course is for, and what the school has.** *(Intake: `knowledge/intake.json`; the
effects of each type: `knowledge/course-type.json`.)*
The course type is declared at intake and changes the build:

- `NEW_ENTRANT` — no prior knowledge. More theory and explanation, more screens, more worked
  examples, step-by-step build-up. When in doubt, explain more: missing an important point is worse
  than one extra slide. More explanation means **more screens**, not denser ones — and every one of
  them still carries enough theory to teach from (L36).
- `EXPERIENCED` — upgrade, advanced, revalidation. Theory still present, shorter, anchored in real
  experience — incidents, scenarios, "what would you do". More digital tasks and scenario exercises.

Either way the course's own language stays fully professional — real terminology, real
abbreviations, real procedures. Plain language (L25) is for the operator, never for the course.

Every instrument and simulator the IMO model course lists for the course is **assumed available at
Novikontas**. Practical tasks are designed for it; the factory does not ask whether the school has it.
→ built out at intake (step 2) and in the build (step 7).

**L29 · The words are approved before the HTML.**
Before any HTML, each module gets a **content script**: the exact, word-for-word text of every
slide (not a description of it), the visual planned for each, the instructor notes — key points
and cues, not a speech *(2.17.0, owner: the notes carry what the instructor explains, adds or asks
beyond the slide, enough to teach from — L36)* — and every self-check and module-check question with its correct answer
and feedback; for the course, the final-assessment bank with answers. It is delivered as a page
that opens with a double-click and prints to PDF, plus an editable twin. The operator corrects it
in chat, in comments or in the twin; the corrections are applied back. **Nothing moves to HTML
until the operator approves it**, and the built slides must then say exactly what was approved.

Every fact the operator stated rather than a source (L26) appears in that module's review **once, in
one short list, marked *operator-stated*** — so it is checked before the HTML, not discovered in front
of a class. One list per module; not a warning beside each one. (Owner, 2026-09-30.)

As the owner set it for step 5 (2026-09-30):

- **the editable copy is a Word file**, not Markdown — colleagues do not use Markdown. Corrections may
  be typed into the text or made as Word comments; both are read. Tracked changes are read as they
  would stand if accepted, and the list says which were tracked and by whom; what cannot be read
  reliably (a box deleted outright, text typed outside the boxes) is said plainly, never guessed;
- **before any correction is applied** — from the Word file, a PDF or the chat — the operator is shown
  a short plain list of what was understood (*"slide 7: X becomes Y; question 3: answer changed to B"*),
  and it is applied only after they confirm;
- **self-checks and the module check are shown in screen order, one task per screen**, as the trainee
  will see them. *(2.17.0: shown on the trainee tablet part of the review, each opened by its "task
  starts" slide - L35.)*

→ built out in 2.16.0: `script/GUIDE.md`, `scripts/content_script.py`, `scripts/check_script_match.py`.

And, as the owner added in 2.16.1: the slide-text check (L22 — internal abbreviations, a model course
cited as a source, version control on the opening slide, the factory's own markers) runs **on the
content script, before approval**, and its findings are shown on the review page. The point of
Stage 3 is to catch these before HTML.

**L30 · Module 1 is a pilot.**
After the architecture is approved, Module 1 alone is scripted, built and approved before any other
module is built. Five roles build it, each an agent with its own context: deck builder, test
builder, visual sourcer, motion and 3D, QA. Only then may the remaining modules run in parallel —
each still with its own script STOP and its own review STOP. → built out in step 10.

**L31 · Ask like a colleague, not like a form.**
The operator knows the subject and will correct what is wrong. So: no "needs SME review" on every
item, and no waiting for them to confirm things they will simply correct. When a real expert
question would clearly improve the result, collect it and ask it at the next STOP — **batched, as
a pop-up question with options** (the ask-question tool), then carry on. Honesty markers —
`UNKNOWN`, `PLACEHOLDER`, `PROVISIONAL`, `[VERIFY: …]` — are written in `factory-notes.md`, never on
a slide (L22), and are **never a reason to stop the work**. The operator's "next" at a STOP ratifies
what that STOP showed, re-expressed Sub-ILOs included.

**L32 · The factory remembers.**
Each course keeps `COURSE_STATE.md` — current stage, approved decisions, open questions, next
step, file map — updated at the end of every stage, so a new session resumes without re-analysing
what is settled. Every correction the operator makes is logged in the course's `FEEDBACK_LOG.md`.
When the course is finished and the operator says they are happy, the factory offers to save the
lessons as a pattern file (what they preferred, what they changed, examples). Future courses read
the available patterns as a starting reference — guidance, not law, and never above the
operator's current request.

The pattern file, as the owner set it (2026-09-30):

- it is **shown to the operator in plain language before it is saved**, and saved only after they
  approve it; they may edit or remove any point;
- it **names the course, the course type and who made it** (and the subject), so a later course
  can judge whether it fits at all — approval is refused until those are filled in;
- the approver's name and the date are written into it; a draft, or a file with no approval, is
  never offered to a later course;
- patterns stay **guidance for future courses, never rules**, and never above the current
  operator's request.

→ built out in 2.14.0 (step 3): `scripts/course_memory.py`, `templates/COURSE_STATE.md`,
`templates/FEEDBACK_LOG.md`, `templates/COURSE_PATTERN.md`, `resources/course-patterns/`.

**L33 · Pictures: find first, keep what teaches, never invent what a trainee must recognise.**
Sourcing order: knowledge base → old course → source files → internet (real photographs,
legitimate schematics) → authored → generated. Legitimate schematics and example pictures from the
knowledge base or the old course are **kept and used** where they teach well, not redrawn for the
sake of it.

- Novikontas's own material — old courses, own manuals, own photographs — is used freely.
- A textbook or publisher figure is **redrawn** as Novikontas's own drawing, **technically
  identical to the original — never simplified**, credited *"after <book>"*, and listed in
  `factory-notes.md` so the owner can check the licence with management. If Novikontas is licensed,
  the original replaces the redraw.
- ICS/SIGTTO figures marked *not cleared for issue or publication* stay out.
- Equipment the trainee must recognise in real life — markings, controls, valves, PPE — is **never**
  an AI image: use an accurate schematic, and add the item to the **"photos to take at Novikontas"**
  list, because the school has the equipment.
- AI illustrations, labelled *"AI-generated illustration"*, are for general context images only.

Never stop at "I can't make this picture": find it, generate it where that is allowed, or finish
everything else and leave the ready-to-run handoff (L23). → built out in `course-visuals` (step 8).

---

### Added by the owner after reviewing the example pages (2026-09-30, 2.17.0)

**L34 · One module per programme topic; the final assessment is the last module, and nothing else.**
*"Modules need to be as many as in the study programme - GAS BASIC has 22 modules/topics, each with its
own academic hours, and an academic hour is 40 min. Module 23 is the assessment task, only the task."*

- Every topic of the approved programme's topic/hours table is its own module, numbered and ordered as
  the programme numbers it, with exactly that topic's theory and practice hours. Topics are never merged
  into one module and never split across two.
- The programme's final-assessment topic (GAS BASIC: topic 23, 2 h) is the **last module** and is the
  assessment only: no slides, no teaching, no self-check. It is not "outside the modules".
- An academic hour is what the programme says; at Novikontas it is 40 minutes, used when the programme
  is silent - and the architecture page says so.
- This replaces `hours/GUIDE.md` step 3's "you may combine topics into a module freely" and step 2's
  final assessment "outside the modules"; both are marked there.
- → `scripts/make_architecture_page.py`, `scripts/test_architecture_page.py`.

**L35 · Two tablets: the slides on the instructor's, the tasks on the trainee's, and the instructor opens every task.**
*"I have tablets: one for the instructor, with a terminal that mirrors the screen on the web, and a tablet
for the trainee where there are only tests."* And: *"When it is time for a task, the slide only explains
that there will now be a task, and on the instructor's panel there is a button OPEN TASK; after that it
opens automatically on each trainee tablet. The trainee cannot see all tasks on one page or navigate
through them - only when the instructor opens that task - and there are no other buttons like ALL TASKS
or back to all module tasks."*

- **Instructor tablet:** the slides, mirrored to the classroom screen; the notes on the instructor's panel
  only. A task is never on a slide. At task time the slide is a *task starts* slide - what the task is
  about, nothing more - and the panel has one button, OPEN TASK.
- **Trainee tablet:** tasks only - self-checks, module checks, the final assessment. A task opens on every
  trainee tablet by itself when the instructor presses OPEN TASK, and only then. No task list, no
  browsing, no way to open another task, no "all tasks", "module tasks" or "back to tasks" button.
  One question per screen, Next → Next, and at the end the trainee's own score.
- **Scores:** self-checks and module checks show the trainee their own score - it is for them - and do not
  count. The instructor sees done / not done and the result as information, never pass/fail, never red.
  The final assessment is the only graded test.
- This supersedes the trainee-side task list, "module tasks" page and task-to-task navigation in
  `course-task-ux` §3; those rulings are marked there. The tablet app's web files do not work this way
  yet: the factory writes the exact change list and the owner applies it (L21, Q1) - step 6.
- → `scripts/content_script.py` (task slides, the two parts of the review), `knowledge/theory-rules.json`
  (`tablets`), `scripts/make_architecture_page.py`.

**L36 · Enough theory before any task.**
*"Slide text is too small - a little amount of words; I doubt the instructor will get through it, and with
that little information can the topic be taught?"* And: *"Before a self-check there should be enough
theory so the trainee can actually do that task and understand it - not 100 words of theory and the task
already."*

- A slide carries the teaching itself - the facts, numbers, names and reasons the Sub-ILO needs - not a
  headline for the instructor to fill in; the instructor notes carry what the instructor explains, adds or
  asks beyond it.
- A module's words fill its minutes; a self-check comes only after a block of new theory; every question's
  answer is in the slides the trainee has already seen; a module too short for a self-check has only its
  module check.
- The numbers are in `knowledge/theory-rules.json` (50-150 words on a slide, 30 in the notes, 40 words per
  theory minute, 10 min and 400 words before a self-check, 60 % of an answer's key words already taught)
  and nowhere else. Every finding is shown on the review page; approval is refused while a must-fix one
  stands, unless the operator approves despite it (L26), which is recorded.
- This refines `course-module-ux`'s compactness budgets: those govern the instructor's *working* screens
  during a session (runner cards, pre-flight), not a theory slide, which must carry the theory.
- → `scripts/content_script.py` (`theory_findings`), `scripts/make_architecture_page.py` (whether the
  planned self-checks fit).
