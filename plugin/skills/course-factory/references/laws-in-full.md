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
