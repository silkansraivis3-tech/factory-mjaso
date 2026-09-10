# Build lane — one page, and every block on it

**v1 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Read this only when the task is building a module page from scratch, or adding screens to one.
Converting an existing multi-page module is `convert/GUIDE.md`; measuring is `measure/GUIDE.md`.

The two authorities for this lane are data, not prose — read them, do not ask me to restate
them:

- `build/knowledge/screen-kinds.json` — what screens a module may contain, the markup contract
  on `section.slide`, and what each kind must and must not carry.
- `build/knowledge/audience-split.json` — where each item goes: the projected screen, or the
  instructor's own channel.

---

## 1 · Start from the timetable, not from the slides

The one defect this order exists to prevent: a module with a block that has no screen. Under
the old multi-page model that was survivable, because every block had its own page and its own
buttons. On one page it is fatal — the deck runs A1 → A2 → A3 → A5 and the missing block
**never happens.** A real module was skipping **90 of its 220 minutes** this way, across two
blocks, and nobody noticed because the page looked complete.

So:

1. Write down every block of the timetable, with its minutes.
2. Give each block **at least one screen**, and as many as the block's work needs.
3. Add up `data-mins`. Compare against the approved hours. **State the answer**, including an
   over-run, in a banner and in the delivery notes. Do not quietly re-time blocks to make the
   total fit, and never print a total you have not added up.

Then present the inventory table from the router's gate and wait for approval. Building
fourteen screens you then have to renumber is the cost of skipping this.

**Expect the count to grow.** Real conversions on one project: 6 → 18 screens, 7 → 12,
8 → 14, 10 → 14. That is not bloat. It is the work that used to live on separate pages
becoming visible.

---

## 2 · Everything the session needs becomes a screen

Each of these was a separate page, a handout, or an unrecorded conversation in the old model,
and each becomes screens now:

| What used to be elsewhere | Now |
|---|---|
| A page saying "open task T1 on the tablets" | an **activity-launch** screen carrying `data-activity="T1"` |
| A practical write-up document | **practical-run** screens — as many as the run needs |
| A marking sheet's criteria section | a **marking** screen — the criteria in the trainee's hearing, the craft in `data-cue` |
| A debrief the instructor was trusted to remember | a **debrief** screen with the questions and the stop condition |
| The module check as a separate assessment page | the **last screen**, always |

A launch screen that is already at 100 % fill cannot also tell the instructor *"the next five
screens are the description of P1, screens 4–8."* That line belongs in the generated instructor
run script — `runscript/GUIDE.md`.

---

## 3 · Zero `<a href>` inside any slide — and how to actually check it

Counting links in the whole file is **not the check.** The landing screen and the footer have
legitimate links, and they will drown a per-slide failure. Carve each `section.slide` out of
the source and search inside it:

```bash
python measure/scripts/check_static.py slide-links path/to/module.html
```

Exit 0 = zero links inside any slide. Non-zero = it names the slide index, the `data-block` and
the href.

Do this after **every** editing pass, not once at the end. A link gets reintroduced by copying
a screen that had one.

---

## 4 · The landing screen keeps a step runner, and it collapses to about two steps

Use the bundled engine: copy `assets/gb_run.js` and `assets/gb_run.css` into the module's own
`assets/`. Do not rewrite the engine per module.

```js
GBRunStart({ key:"m5", steps:STEPS, button:"#gbStart" });

var STEPS = [
  { n:"1", mins:220, title:"Open the presentation and finish it",
    open:{ label:"▶ Start the presentation", href:"presentation/index.html" },
    they:"Eighteen screens. Every activity is announced on its own screen.",
    done:"You reached the last screen and the check is finished." },
  { n:"2", mins:20, title:"Record the results",
    open:{ label:"Open the record", href:"assessment/record.html" },
    they:"Nothing — the trainees are finished.",
    done:"Every trainee has a result and you have copied the record out." }
];
```

Rules that are load-bearing:

- **Every step carries `mins:`.** A step without it renders with no duration badge while every
  other module shows one. `screen-kinds.json` states this as required; the check is
  `python measure/scripts/check_static.py mins path/to/START_HERE.html`.
- **The deck announces, it never launches.** No screen writes a progress counter and no screen
  points the projector at a trainee's page. See `convert/GUIDE.md` for what was removed and
  why — if you are building new, simply never add it.
- **A page that is not a step never gets an advancing button.** In this architecture almost
  nothing is a page any more, so this mostly means: do not give the module page a
  `next:`/`finish:true` declaration. A page that declares `next` advances the module's stored
  step counter **merely by being opened.**
- The entry screen must say when it is **resuming** — a big button that silently opens the
  middle of a module gives the instructor no way to know why. `GBRunStart` renders the strip;
  keep it.

---

## 5 · The audience rule, applied item by item

Route every item through `build/knowledge/audience-split.json`. Two things about it in
practice:

**It is per item, not per screen.** A marking screen almost always splits: the criteria are
the trainee's, the strictness is the instructor's. Do not move a whole screen because half of
it was instructor-only.

**`data-cue` is where the borderline goes.** It is an attribute on the slide, never rendered,
revealed on the instructor's own key. Because it costs nothing, a wrong guess towards the cue
is cheap and a wrong guess towards the projected screen is not.

Then run the pronoun test over every visible line: **is there a second-person "you" that means
the instructor?** `"the technique you demonstrated"` on a projected screen reads to a trainee
as if they demonstrated it. Rewrite in the third person, or move the item.

---

## 6 · The module check is the last screen

From `screen-kinds.json`, and worth repeating because it is the screen most often got wrong:
zero links, nothing recorded on it, and **the words "record" and "score" do not appear.** No
ILO codes, no provenance note, no item count. It is read by the room while they are being
assessed; recording is the instructor's job on the instructor's own device.

```bash
python measure/scripts/check_static.py check-screen path/to/module.html
```

---

## 7 · Compactness budgets

Over budget is a defect, the same as a broken link.

| Surface | Budget |
|---|---|
| A runner step card | ≤ 45 words total, one primary button, `they` ≤ 20 words, `done` ≤ 15 |
| A working screen the instructor holds mid-session | ≤ ~70 visible words |
| Any paragraph on a page opened during a session | ≤ 45 words |
| A pre-flight item | ≤ 25 words |
| Provenance and sourcing | footer only, never in the body |

Cut, every time: any sentence telling the instructor what to say; any restatement of something
another artefact owns; any justification nobody asked for; any adjective doing no work
(*carefully*, *properly*, *thoroughly*); motivational prose beyond one line per module;
duplicated warnings.

**But cross-check after every collapse.** Read only the visible text, aloud, and list what you
would have to go looking for. Anything on that list comes back up. A visible line carries the
number, name or limit that makes it actionable:

| Not sufficient | Sufficient |
|---|---|
| Load the starting condition. | Load state **A** — tanks full of air, alongside — on every station. |
| Mark the criteria as you go. | Mark **items 1, 2 and 3** — the ones this task evidences. |
| Check the readings are within limits. | Stop at **dew point −25 °C**; they read it on the tank overview. |

**Plain language governs the navigation, not the subject.** Step titles, button labels, tab
labels, the do-this-now lines and pre-flight items get words that need nothing looked up.
Projected slides, task cards, criteria, quoted regulation and ILOs keep the full professional
register, because the vocabulary **is** the competence. Never simplify a technical term, a set
point or a quoted criterion to make a page feel friendlier — that is content damage, and it is
outside this skill's scope.

The one exception that proves the rule: an equipment vendor's own tooling vocabulary may be
translated, because the tooling is not the subject. *"The console comprises six pages"* becomes
*"the simulator shows pictures of the ship's cargo system that you can click, grouped into tabs
along the bottom"* — and keep the source term as the label, because that is what is printed on
the machine. Also **name what to ignore**: *"the other two tabs are not used in this module"* is
as useful as naming what to open.

---

## 8 · Anything a trainee or instructor fills in

Pick the record engine by **what produced the result**, never by taste. Getting it wrong means
an instructor retyping something a machine already knew, or a six-criterion judgement squeezed
into one number.

| The assessment is | Records |
|---|---|
| a **self-marking tablet task** | one score per trainee, verdict derived from the pass rule |
| the **instructor watching** against a fixed criteria list on a scale | a mark per criterion, verdict computed from the rule |
| one score **plus** a free verdict | name, group, score, verdict, note |

Whatever the engine, these rules are the ones that produced real data loss when broken:

- **Quote the criteria; do not paraphrase them.** They are approved assessment wording.
- **The pass rule lives in configuration, not in prose.** A card that shows *"4 of 6"* until
  every item is marked, and only then a verdict, cannot be finished from memory at 17:00 —
  which is the point. An override that contradicts the rule must raise an inline warning naming
  the contradiction, not silently accept it.
- **A pre-filled placeholder is not an answer.** Never ship `value="PASSED / NOT PASSED"`.
- **Every dead glyph becomes a real control.** `☐ yes ☐ partly ☐ no` is three radio pills.
- **Wrap every storage read and write**, and tell the user in the bar when storage is blocked.
  Never silently lose an hour of group work.
- **Restored radio pills must be repainted.** Restoring sets `.checked` directly and fires no
  `change` event, so the repaint has to run after the boot restore, after a record switch and
  after a clear.
- **A debounce that never flushes loses the last thing typed.** Bind the flush to
  `beforeunload`, `pagehide` **and** `visibilitychange → hidden`. An instructor types a score
  and immediately taps the bar; an Android tablet gets backgrounded mid-row. This was a real
  data-loss bug found in testing.
- **Say what is true in the footer**: saved in this tablet's browser only, never sent anywhere,
  no other device can see it, clearing site data clears it. Do not imply a backup — and do not
  collapse that honesty, because it changes what the instructor does before leaving the room.

**Replacing a form is the highest-risk edit there is.** Two evidence losses got through on one
project, both when a printed form became a digital one, and both invisible to a line-level
diff, because what was lost was a **field, not a paragraph** — a *roles held* column, a
*delivery-mode* block, an observed judgement that was the only evidence a 20-minute slot
happened. Before deleting any form: list every field with what it is evidence *of*, map each
one to the replacement or write down why it is going, then **sentence-diff** the page
afterwards.

---

## 9 · Never animate into visibility

The resting CSS state must already be correct and already visible. A preview pane stalls
`requestAnimationFrame` and CSS animations, so anything that fades or slides in from `opacity:0`
can simply never arrive — and it looks like a blank screen, not like a bug.

Always add:

```css
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
```

The same physics is why measuring is hard — see `measure/GUIDE.md` §1.

---

## 10 · After any scripted edit to inline JavaScript, load the page and read the console

Not optional, and not replaceable by reading the diff. Two real failures:

- A comment replacement left the old comment's tail as bare JavaScript and **killed an entire
  script**, while the page still looked fine.
- A missing comma in a generated object literal **silently disabled every button** on two task
  pages.

`node` may not be installed on the machine, in which case the browser console is the only
syntax check you have. Use it.

---

## 11 · Delivery constraints

No CDN — a webfont `<link>` with a full fallback stack is the only exception. No runtime
server, no backend, no build step for delivery. The module must run from a shared drive and
from a single-file package. Shared CSS/JS lives in the module's own `assets/` and is inlined by
the single-file build: verify the built page reports **0 external stylesheets and 0 external
scripts**, and that the build inlines *every* local stylesheet and script rather than one by
name. A build that resolves links by **filename** rather than by path will silently collapse a
module's several `index.html` files onto one route.

**Never deploy automatically.** Build, report, hand over.


---

## Titles, photographs, and one plan per module *(added 2026-09-07)*

### A title names what is on the screen

Owner, on a title of mine — *"The four roles, and why the seat moves"*:

> "its just nonsense, please avoid this shit in future, it sounds maximally as ai and it does not
> make sense, its like no context nonsense text"

Correct. "The seat" has no antecedent; the title only parses once you are already looking at the
diagram, which is precisely when a title is useless. Titles are read in a hover label, a jump
rail, a run script and a contents list — **all with the screen not visible**.

Four tests, and a title must pass all of them:

1. **No metaphor, no hook, no riddle.** The same pass found two more of mine: *"the shape that
   fits the way out"* (a stretcher that fits a manhole — say that) and one that trailed off
   mid-sentence at *"…and watch it"*.
2. **Never truncate a sentence to shorten a title.** If the `<h2>` is long, write a shorter
   *title*; do not cut the h2 mid-clause.
3. **It must parse with the screen not visible.**
4. **Reuse the deck's existing idiom** before inventing a shape — the course already had
   *"Interactive — the flammable range"* as a pattern.

The boring version is the correct one. This applies to anything that names something: screen
titles, step labels, task names, section headings.

### Never squeeze a photograph

If a screen cannot afford a picture, **the picture gets its own screen**. Do not shrink it, and do
not put it on a screen about something else.

A stylesheet here once admitted the compromise in its own comment — "the one screen where the
photographs had to be paid for" — and documented buying back 34px by dropping a photo strip to
120px. In a 90px frame a 795×2200 portrait renders **32px wide**. The owner's verdict was "why
these pictures is so shriked". An audit that measures overflow treats the photograph as the
elastic thing, because it is the variable that gives; but below about 200px a photograph is not a
photograph, so the "fix" trades a measurable defect for an unmeasurable one.

Two related rules:

- **Read the photo's own metadata warning before placing it.** One file carried
  *"a generic workplace MSDS, **not** a liquefied-gas cargo data sheet to ICS Appendix 1 — caption
  must say so"*. Its visible blocks differ from the ones the module teaches, so putting it beside
  the module's block map would teach the wrong artefact. It was **not** placed, and the module
  having no photograph was logged as a photo request instead. A module with no picture is better
  than a module with the wrong one.
- **Count photo usage across the whole product, not just the deck.** "Module 5 uses 5 of 15" was
  wrong: the rest are in the tablet task and the handout, which is where a trainee picks kit.
  Never cap a figure with a percentage of a percentage either — a drawing capped at 44 % of a box
  itself capped at 38 % of a card opened at 67×47 inside a 1015×115 white frame.

### One plan per module, stating its own minutes

Every module carries exactly **one** plan document, and it states its allocated and built minutes
on its own face. One deck's plan does this well — its header reads
*"8 academic hours = 320 min | Teaching below: 330 min"* — which self-reports the gap where
anyone can see it.

GAS BASIC has no plan for two of its eight modules and a differently-marked one for a third, so
its timings could not be summed from a single source and the 33 % overrun went unnoticed until
every module existed. `course-factory`'s hours lane owns the arithmetic; this is the artefact it
reads.
