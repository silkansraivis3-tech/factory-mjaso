# Fix lane — find, one list, one yes, change, one check (L50)

**v1 (2026-10-15) · Maintained by Raivis · part of the `course-factory` plugin, shared with colleagues through the marketplace**

Read this when the operator wants something changed - or rebuilt - in modules that are **already built**: one
module, some, or all (§3b: a rebuild is a fix too). "The last slide is bad in all modules, make it like this." "Modules 1–3 have too much free space, find it in
the others." "Text bigger everywhere." "Slide 7 in module 4 says X, it should say Y." A fix is **not a build**:
it touches a few things, so it checks those things, once.

> Owner, 2026-10-15: *"i want for fixes to be faster and still quality. like if i find that in module 1-3 is very
> much free space, i can tell claude to find all free spaces in other modules, and it will not go to 3-4 qa reviews
> before that, because it takes time and usage."*

Why this lane exists: on GAS ADVANCED a module took 1–1.5 h to build and a small fix about 30 minutes, because every
fix ran the build's whole process — a fixer agent per module re-measuring every slide at two sizes, the orchestrator
re-checking it, a whole-course QA, a visual sweep, up to six agents at once until the PC stopped (FEEDBACK_LOG
#61–#93). The numbers and limits live in **`knowledge/fix-rules.json`**; this page says how to work.

---

## 0 · Read only this

`fix/GUIDE.md` (this page), the course's `working_claude\COURSE_STATE.md` and `working_claude\STANDARDS.md`. Not
SKILL.md's laws in full, not the build lanes, not every module's notes. Open a lane guide only if the fix needs its
craft — `course-module-ui` for a colour or a component's look, `course-task-ux` for a task page — and then only the
part you need. The approved words are still locked (L29) and the four material limits still hold (L26); everything
else about a fix is in this page.

## 1 · Find — every place at once

When the operator names a problem and says *"in the others too / all modules / find the same"*, **sweep first**,
before changing anything:

```
python scripts/fix.py sweep <course> --find space        slides with too much free space
python scripts/fix.py sweep <course> --find text         text too small for the room
python scripts/fix.py sweep <course> --find overflow     content that runs off the slide
python scripts/fix.py sweep <course> --find layout       all three - it is one measurement
python scripts/fix.py sweep <course> --find last-slide --like 2      every module's end slide, against module 2's
python scripts/fix.py sweep <course> --find kind --kind Task         every slide of one kind
python scripts/fix.py sweep <course> --find words --words "Next: Module"   every place that says it
      --modules 1-3,7   only these;  --floor 18   a stricter text floor
```

The measured sweeps open every module in a hidden browser at 1280 × 800, press Start and Next to the end, let every
animation finish, and measure each slide (`scripts/measure_slides.py`) — about four seconds a module, the same
numbers every run. Nobody opens a browser pane, pastes a probe or walks a deck by hand.

When the operator's example is a module they already looked at (*"like in modules 1–3"*), sweep those modules too:
the numbers there are what *"too much free space"* means to them. If the thresholds in `fix-rules.json` disagree with
what they pointed at, use theirs (`--floor`), and say the number in one line.

## 2 · One list, one yes

Show the sweep's numbered list **once**, in the operator's words: module, slide, title, what is wrong. Slides that
are sparer by design (task start, check, opener, end) are listed apart — they decide. One answer covers all of it:
*"yes"*, *"all except 4 and 9"*, *"only the teaching slides"*. Do not ask per module, do not re-ask after each one.

**Words** — titles, slide text, instructor notes — across any number of modules go through the content scripts,
because the slides must say what was approved (L29):

```
python scripts/fix.py propose <course> --changes changes.json     ONE list for every module; nothing changed yet
python scripts/fix.py apply   <course> --confirmed                after the one yes
python scripts/fix.py approve <course> --by "<name>"              one approval for the whole batch
```

`changes.json` is `[{"module": 3, "field": "s07.title", "new": "..."}, ...]`. `apply` changes each module's script
exactly as `content_script.py apply` does (old words kept, FEEDBACK_LOG, fresh review page and Word file) **and puts
the same words into the built slides**; a slide where that would mean guessing (the number of lines changed, a line
with bold or a link inside it) is listed as hand work — do that slide by hand. A wording the operator gave in chat is
their approval (L26): `approve --by` with their name, once.

## 3 · Change — once, where it lives

- **A part every module uses** — the end-slide recap, the full-screen viewer, the touch sizes — is changed **once**,
  in `course\working_claude\shared\`, then copied into every module:
  `python scripts/fix.py sync-shared <course>` (dry run: what would change) → `--confirmed`. Each module keeps its own
  copy (L43); nobody edits nineteen copies. A file that belongs somewhere other than `assets\` is mapped in
  `shared\shared.json`: `{"gb_recap.css": "assets/css/gb_recap.css"}`.
- **A module built by its own generator** (`working_claude\build\M04\gen\...`): change the generator or its data,
  rebuild — never only the output, or the next rebuild brings the old version back (GAS ADVANCED #88).
- **Hand work** (re-composing a slide, a bigger picture, less padding): do it in this session. Agents only when the
  hand work spans more than three modules — **at most two at once**, each given its modules, the sweep's list and
  this page; **no QA agent after them**.
- **A design wish against a factory rule** — *"no recap in my modules"*, *"our own blue"*, *"smaller text here"* —
  is the person's to make (L26): say the rule and the risk once (`design_choices.py rules`), and on *their way* do it
  and record it: `fix.py standard <course> --add "<the choice>" --said "<their words>" --departs <rule> --risk "..."`.
  Every check then reports it as their choice. **Never "fix" a recorded choice** - a sweep or check that lists one
  lists it as theirs.
- **A wish for every module** — *"the last slide like this"*, *"text bigger"*, *"all buttons 56 px"* — is also a
  **standard**, written once so new modules are built to it and it is never repaired again:
  `python scripts/fix.py standard <course> --add "<the rule>" --said "<their words>"`.

## 3b · A rebuild is a fix too — and so is one change in one built module (2.65.0)

> Owner, 2026-10-26: *"when I want to rebuild or fix something, it does not go through the same thing, it goes through the fix process"*

A module that is **already built** - a newer factory version, a changed build sheet, a new design file - is built again
from its **approved** words in the fix lane, not by the build's whole process:

```
python scripts/fix.py rebuild <course> --modules 1        one module; 1-3,7 for several; no --modules: all built ones
```

For each module: the **pre-check** (`compile/scripts/precheck.py`, a second - a missing picture, a photograph under
800 px, dense text with no picture: the module is not rebuilt until that is fixed), the factory's **design files**,
the **compile** with its own drawing check on what changed. Then **one check** for all of them - the build's own
audits (`run_audits.py`, 1280 x 800 and 1024 x 768: judged exactly as a build is) and the course package. No figure
stage, no review sheets, no QA agent: a rebuild changes no words. What only the full build settles - a drawing that no
longer fits its slide, a slide that scrolls - is named, module by module: run
`compile/scripts/build_module.py <course> --module N` for that module alone. A module built before is not stopped there
by the small pictures it already has: they are notes, as in the rebuild (2.65.1).

**One named change in one built module** ("slide 7 says X, it should say Y", "a bigger picture on slide 4") is a fix as
well: words through `fix.py propose / apply / approve`, anything else changed in place, then the **one** `fix.py check`
for its kind (§4). A module that is not built yet still goes the build's way.

## 4 · One check — only what the change can break, once

| The change was | Run | It proves |
|---|---|---|
| words, titles, notes | `fix.py check <course> --kind words` | the touched modules say exactly the approved words; nothing on them a trainee must not read |
| space, size, position, spacing, CSS, a bigger picture | `fix.py check <course> --kind layout --modules ... [--slides s03,s07]` | nothing off the screen, no text under the floor; for swept slides **before → after** |
| a file added, moved, renamed, linked; a shared file copied | `fix.py check <course> --kind package` | the classroom system still takes the course |
| a new or changed component, animation, interaction | `--kind layout`, then **one look at one changed slide** in the browser pane | it works and looks right — one slide, not every slide of every module |

Run by whoever made the fix, once. Report its numbers. **Not in a fix** (`fix-rules.json → never_in_a_fix`): a second
checker, an orchestrator re-check, a whole-course QA, re-measuring slides nobody touched, a second screen size unless
the operator asked about the projector, a screenshot of every slide, more than two agents. The full sign-off — the
fourteen checks in SKILL.md — stays for building a module, a retrofit and the handover.

If the check fails, fix what it names and run **that** check again — not the others.

## 5 · Tell the operator — Done · Check now · Next (L25)

- **Done** — what changed, in how many modules: *"free space taken out of 14 slides in modules 4–19"*.
- **Check now** — two or three slides worth looking at (the worst before), with the module and slide number, and how
  to open them. Not the whole list.
- **Next** — anything left: hand work not done, a standard to confirm, a question as a pop-up (L31).

Then log it: the operator's words in `FEEDBACK_LOG.md` (L32) — `apply` already does this for words — and one line in
`COURSE_STATE.md`.

## A worked example — the owner's own

*"In modules 1–3 there is very much free space. Find it in the other modules and fix it."*

1. `fix.py sweep <course> --find space` — one run, all modules, ~80 s for nineteen. Modules 1–3 are in it, so their
   numbers set what "much" means.
2. Show the list once: *"18 teaching slides in 9 modules, and 12 task-start slides listed apart."* — *"yes, all
   teaching ones."*
3. Re-compose those slides: bigger figures, the text block filling its column, less padding — in the module's source
   (its generator, if it has one); for a padding that is wrong in every module, in the shared stylesheet, then
   `sync-shared`. Add the standard: *"teaching slides use the screen: content ≥ 45 %, no empty band below"*.
4. `fix.py check <course> --kind layout --modules 4,6,9...` — once: nothing off the screen, no text under 16 px,
   each slide's *before → after*.
5. Done · Check now · Next. No second QA.
