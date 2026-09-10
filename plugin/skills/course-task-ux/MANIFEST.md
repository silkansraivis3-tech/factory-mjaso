# MANIFEST — course-task-ux

**v2 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Maintainer file. **Never read at runtime.** It exists so a session six months from now — one
with no memory of why any of this is the way it is — can pick the skill up cold.

## 0 · What changed in v2, and why

v1 was a single 210-line `SKILL.md`: no header line, no MANIFEST, no assets, no scripts. It
was already good and already close to course-agnostic. v2 does two things and deliberately
not a third:

1. **Made it portable.** The owner's ask: *"also make skill out of tasks, how to create them
   and how they need to look, after that i will in another claude code use on other study
   program"*, plus the standing instruction that the skills be course-agnostic. So: no
   absolute paths, no assumption that this machine's folders exist, the reference
   implementation named out of the rules (v1 opened with "Module 1's tasks are the reference
   implementation" — a sentence that is unusable in another programme), course codes and
   module numbers demoted to marked examples, and the delivery target restated as a
   parameter to be re-measured rather than a fact to inherit.
2. **Completed it.** Seven defects that hit during the delivery of 32 task screens across
   eight modules were absent from v1. They are now §5, §9, §10, §12, §13, §14, and two
   additions to the §11 traps.
3. **Did not renumber or soften the existing rules.** §§1–4 and §6–8 carry v1's rules and,
   more importantly, v1's verbatim owner quotes. The quotes are the evidence — they are why a
   rule survives an argument about taste. Removing them to make the file "cleaner" would
   quietly convert a ruling into an opinion.

Version numbering: the v1 file carried no version at all, so calling this v2 records that
there is a substantially different earlier state, even though nothing on disk says v1.

## 1 · Design principles

- **The screen, never the assessment.** This skill decides how a task looks and behaves. What
  a task assesses, whether the answer key is right, and which ILO it covers all live in the
  exercise skills. That line is what keeps the bundle small and makes it portable to a
  programme with no maritime content in it at all.
- **Owner quotes are load-bearing.** Each rule keeps the sentence that produced it. A new
  programme reads them as evidence from a previous course, not as facts about its own.
- **The delivery target is a parameter.** Every number in §11 is tagged to an 800 × 1280
  portrait WebView. A new device re-measures; it does not inherit. What survives a device
  change is stated explicitly at the top of `SKILL.md` so a reader can tell which half of the
  standard is physics and which half is pedagogy.
- **Anything checkable by code is checked by code.** Five static sweeps and an in-page probe,
  with exit codes. A rule enforced by a model remembering it is a rule that holds until the
  session gets long.
- **A skipped check is not a pass.** `check_task_pages.py` exits **3** — distinct from both 0
  and 1 — when a check could not run. That exists because `node` is not installed on the
  reference machine, and a syntax check silently skipped is exactly how the missing-comma
  defect in §12 survived long enough to kill two pages.
- **A clean report is more dangerous than a failing one.** The probe refuses to run in a
  small viewport rather than reporting from a 0 × 0 pane.
- **Bundle the engines the standard depends on.** §5 and §9 are not achievable by following
  prose — they are code. Prose that says "give the keyboard a way out" and leaves the reader
  to invent the 120 ms hide timer and the prevented `mousedown` will get a worse keyboard
  escape every time.

## 2 · Architecture — matches disk

```
course-task-ux/
├── SKILL.md                     router + the locked standard. Read fully, always
├── MANIFEST.md                  this file. Never read at runtime
├── references/
│   ├── typed-input.md           read only when a task has a text field: wiring,
│   │                            failure modes, the 7-step manual check
│   └── verify.md                read before signing off any page: order of work,
│                                the script's exit codes, the false-result traps
├── templates/
│   └── task-notes.md            the companion notes file, written during the run.
│                                Routes all four honesty markers and ends in the
│                                feedback-on-this-skill section
├── assets/
│   ├── kbd_escape.css           the Done pill (§5). Genericised from gb_kbd.css
│   ├── kbd_escape.js            three routes out of the soft keyboard (§5)
│   ├── task_complete.css        the completion panel (§9). From gb_done.css
│   └── task_complete.js         one shared ending for every task (§9)
└── scripts/
    ├── check_task_pages.py      five static sweeps; exit 0 / 1 / 2 / 3
    └── measure_in_page.js       pasted into the browser console; the geometry,
                                 type-size and contrast half of §11
```

**No lanes, and that is a decision.** The conventions split into lanes as soon as distinct
modes appear that never run together, and three plausible modes do exist here: build a new
task, convert an old one, review and measure one. They were rejected because **all three read
the same material** — a reviewer needs §§1–14 to review *against*, and a builder needs them
to build. Splitting would either duplicate the standard into three lanes (two of which go
stale silently) or leave three lanes so thin they are just a table of contents. What *is*
genuinely conditional was factored out instead: `references/typed-input.md` loads only for a
task with a text field, and `references/verify.md` only at sign-off. That buys the token
saving a lane split would have bought without inventing a mode boundary that does not exist.
The sibling `course-module-ux` does split into lanes, correctly — its run-script generator
and its contrast audit genuinely share nothing.

## 3 · Provenance

The dedup check was performed before drafting; this is its result.

| Item | Source | Disposition |
|---|---|---|
| `SKILL.md` §§1–4, §§6–8 (no header, answer mechanics, navigation, understandability, tap-to-locate, photographs, two-stage tap) | v1 `course-task-ux` | **Carried** verbatim in substance, including every owner quote. Reworded only to drop this course's identity: "Module 1's tasks are the reference implementation" removed, GAS module numbers and task codes demoted to marked examples |
| `SKILL.md` §11 floor table | v1 §8 | **Carried**, plus the target restated as a parameter and two new traps (0 × 0 pane, SVG text scaling) |
| `SKILL.md` §14 engine drift | v1 §9 | **Carried and sharpened** — added the generated-build-overwrites-hand-edits rule |
| `SKILL.md` §5 keyboard escape + `assets/kbd_escape.*` + `references/typed-input.md` | Delivery defect, 2026-09-02, owner quote. Engine adapted from the reference build's `gb_kbd.js` / `gb_kbd.css` | **New** |
| `SKILL.md` §9 completion state + `assets/task_complete.*` | Delivery ruling 2026-09-01. Engine adapted from `gb_done.js` / `gb_done.css` | **New** |
| `SKILL.md` §10 rendered numbers | Delivery defect: a total computed, declared, never painted, while the record sheet asked for "the score their tablet showed" | **New** |
| `SKILL.md` §12 console after scripted edits | Delivery defect: a generated object literal missing one comma; `SyntaxError`, whole inline script dead, every button on two pages silently inert, page looked perfect | **New** |
| `SKILL.md` §13 dead markup + specs that outrun code | Delivery defects: `<span id="gb-home">` / `gb-deck` read by nothing; a class styled in seven stylesheets and present in one page's markup; a spec mandating an element the reference implementation never had | **New** |
| `scripts/check_task_pages.py`, `scripts/measure_in_page.js` | Written here from the defects above | **New** |
| `templates/task-notes.md` | Conventions §6 companion-file requirement | **New** |
| The one-page module architecture, START HERE, the step runner, the instructor run script, the deck measurement discipline | **`course-module-ux`** (renamed from `gas-basic-module-ux` by its own maintainer on 2026-09-03, mid-session) | **NOT copied — pointed at.** Named in the `SKILL.md` boundary table. Its directory was not touched; another agent owned it during this revision |
| Deck templates, House Rules, copy budgets, slide roles | `novikontas-presentations` | **NOT copied — pointed at.** A task screen is not a slide and shares none of the copy budget machinery |
| Exercise design, answer keys, rubrics, ILO coverage | `novikontas-practical-exercises`, `novikontas-exercise-description-trainee` / `-instructor` | **NOT copied — pointed at.** This skill governs the screen and never what the task assesses. This is the boundary that keeps the bundle course-agnostic |
| Written tests on paper | `novikontas-written-tests` | **NOT copied — pointed at** |
| Brand colour, typography, logo | `novikontas-brandbook` | **NOT copied — pointed at.** The bundled engines expose `--task-accent` / `--task-font-display` with Novikontas defaults rather than restating the palette |
| ILO wording, task depth, sequencing, assessment timing | `novikontas-pedagogy-toolkit` | **NOT copied — pointed at.** Added during this revision: v1 had no pointer to it and §2's answer mechanics sit right next to its territory |
| Skill shape, markers, gates, MANIFEST, revision checklist | `novikontas-skill-conventions` | **NOT copied — followed.** A conventions layer, not content |
| Cost discipline | `novikontas-token-economics` | **NOT copied — run as a pass** |

## 4 · Conflicts found and resolved

1. **`gas-basic-module-ux` vs `course-module-ux`.** The brief named the former; its maintainer
   renamed it to the latter partway through this session. The boundary row and `SKILL.md` both
   point at **`course-module-ux`**, the live name. `gas-basic-module-ux/` is still on disk,
   its own maintainer has since marked its description SUPERSEDED, and this revision did not
   touch that directory — it is another owner's to retire.
2. **Maintainer and status.** The brief's owner quotes are Raivis's (the course owner), while
   the sibling skills carry Ritvars. First resolved in favour of the family, then **corrected
   on review to `Maintained by Raivis`** — the quotes are his and he owns the course; matching
   the family is a later cosmetic concern if anyone asks. Status
   `Personal — installed for Raivis only, not org-published`.
3. **Course-agnostic vs brand-agnostic.** Genericising the engines could have meant stripping
   Novikontas navy and Raleway. It does not: a different *study programme* is still the same
   organisation. The colours moved behind CSS custom properties with the brand values as
   defaults, and `novikontas-brandbook` is named as the authority.
4. **Engine file names.** The reference build's `gb_` prefix means "GAS BASIC" and cannot
   travel. Renamed to `kbd_escape.*` / `task_complete.*`, global `GBDone` → `TaskDone`, id
   `#gbkbd-done` → `#kbd-done`, classes `.gbdone*` → `.taskdone*`. Every file header records
   its previous name so a maintainer of the old course can still map them, and
   `check_task_pages.py --only kbd` accepts **either** name so it can be run against the old
   build without false findings.
5. **How hard to push §10.** The "every asked-for number is rendered" check is not fully
   decidable statically — it depends on a record sheet the script cannot read. Resolved by
   shipping it as an honest heuristic that flags computed-and-never-painted totals as
   *candidates*, with the record sheet named in `SKILL.md` §10 as the authority. The
   alternative — a check that claims to be complete — would be worse than none.

## 5 · Known gaps / before this goes live elsewhere

1. **No real runs yet.** No `task-notes.md` from an actual delivery exists, so the feedback
   loop in conventions §6 has never closed. First run in the new programme should produce
   one, and it should be read at v3.
2. **One untested branch: the `node` path of the syntax check.** `check_task_pages.py --only
   syntax` has **never executed its `node` branch**, because `node` is not installed on this
   machine — the absent-node branch is the one that was exercised, and it correctly exits 3.
   What would verify the other: run it on a machine with `node`, against a page with a
   deliberately broken inline script, and confirm **exit 1 with the `SyntaxError` line**
   rather than exit 3. The fixture for it is in §6 below.
3. **`measure_in_page.js` has not been run in a real Android WebView.** It was verified in a
   desktop browser against a served fixture (see §6) — it parses, measures, correctly finds
   an under-floor tap target, correctly applies the SVG scale, and correctly refuses at
   `innerWidth 0`. What would verify the rest: paste it into a served task page on the target
   tablet and confirm the numbers match a manual measurement.
4. **The `floor` check's known false negatives, accepted deliberately.** It reports nothing
   for `em`, `%`, `calc()` or `var()` sizes, and nothing for SVG `font-size` (deferred to the
   probe with a count). Both are silence-instead-of-guessing, chosen because the browser is
   the authority and a false positive is what makes people stop running the tool. What covers
   them: `measure_in_page.js`, which resolves everything the browser resolved.
5. **`resolve_len` assumes a 16 px root for `rem`.** Correct unless the course sets
   `:root{font-size:…}`. What would verify it: grep the course's stylesheets for a root
   font-size, and if one exists, the resolver needs it passed in.
6. **A page with unquoted HTML attributes has its stylesheets missed.** `linked_assets`
   requires quoted `href`/`src`, so `<link rel=stylesheet href=./s.css>` resolves to nothing
   and the sweep silently sees 0 stylesheets. Found while building the review fixture.
   Workaround: pass `--css`/`--js` explicitly, which is the documented invocation anyway. The
   header line always prints the stylesheet and script counts — **if it says 0, that is the
   bug, not a clean page.**
7. **The `deadmarkup` class sweep is scope-sensitive by nature.** A class used only by a page
   outside the paths given will be reported dead. That is the correct behaviour for a
   per-module check and a false positive for a partial run — pass the whole module, or read
   the finding before deleting. Not fixable without a project-wide index this skill has no
   business owning.
8. **`numbers` is a heuristic** — see conflict 5. It will miss a number rendered through a
   helper it cannot follow, and flag a total that is legitimately internal.
9. **§13's "the spec is the defect" rule has no enforcement.** It is a habit, not a check. A
   script cannot tell which of a spec and a shipped page is right.
10. **The floor has not been re-measured for any device other than 800 × 1280 portrait.** The
   numbers in §11 are honest for that one target and stated as such.

## 6 · Verification performed in the revision session (2026-09-03)

Per conventions §9 — run the check, read the file, then report. Not "it should work".

**The five static sweeps were driven against a fixture built to fail each one** (a page with a
dead `id="gb-home"`, a CSS class present in no markup, a computed-and-never-painted
`scoreTotal`, an 11px font, a 30px tappable rule, a text field with no escape engine, a
contradictory `enterkeyhint="next"`, and a textarea wrongly carrying one), and against a
matching clean page. All four exit codes were observed: **0** clean, **1** findings, **2**
usage error, **3** check-could-not-run (`node` absent).

**Two real bugs were found by that fixture and fixed** — which is the argument for driving a
script rather than reasoning about it:

1. `numbers` reported the fixture clean. A ±200-character window let a `textContent =` on the
   *next* line count as painting the variable — a false pass on the exact defect the check
   exists for. Replaced with `statement_around()`, bounded by `;`, which still keeps a
   multi-line `TaskDone.show({ line: … })` call intact.
2. `deadmarkup`'s class sweep read only external stylesheets, so a dead class inside an
   inline `<style>` block was invisible. Inline blocks are now included, with line offsets so
   findings point at the real line. Also fixed: `height` matching inside `min-height`, which
   reported one 30px rule twice.

**`measure_in_page.js` was verified in a browser against a served fixture** — `node` is absent,
so per §12 the browser was the only syntax check available, which is the rule applied to the
skill's own code:

- parses (`new Function`) and runs;
- found a true positive: a bare `<input type="text">` at **177 × 21 px**, under the 44px floor;
- **the SVG trap reproduced exactly.** A label declared `font-size:12` in a 350-unit viewBox
  rendered 843px wide measured **scale 2.409, painted 28.9px** and was correctly **not**
  flagged — that is the false positive that nearly caused a "fix" to correct type. A second
  label declared at 4px, painted 9.6px, was correctly flagged. Both numbers came out of the
  probe, not out of arithmetic done by hand;
- **the refusal branch fires.** With `innerWidth` stubbed to 0 it returns
  `{ok:false, refused:"REFUSING TO MEASURE: innerWidth is 0…"}` and reports no numbers at all.
  Note the 0 × 0 pane could not be reproduced naturally in-session — the guard was exercised
  by overriding `innerWidth`, not by hiding the pane.

**Positive control against a real shipped page.** `--only kbd --only numbers` was run
read-only against a task page from the reference build that already wires the keyboard escape
and does render its total: **exit 0, no findings**. That confirms the `kbd` check accepts the
old `gb_kbd` file names as well as the new ones, and that `numbers` does not fire on a page
that is correct. Nothing in that repository was modified.

Not verified, and named in §5: the `node` branch of the syntax check, and the probe on a real
Android WebView.

## 6a · The false-positive episode, and what it changed (review round, 2026-09-03)

Reviewed against a real shipped task set — `<course>/modules/m8/tasks` with its own
`--css/--js` — the `floor` check reported **14 findings. All 14 were false**; the same page
measured in a browser at 800 × 1280 gave `htmlSubFloor: 0, svgSubFloor: 0`. This is recorded
in full because the *cause of the cause* matters more than the four bugs.

**Why the fixture missed it.** The fixture caught two real bugs in the first round and then
**agreed with itself about everything else** — it was written from the same misunderstanding
as the code, so it confirmed rather than tested. A fixture built by the author of the checker
validates the author's model, not reality. Every check here is now driven against a real
shipped stylesheet as well.

**Four independent causes, all fixed:**

1. **The clamp rule itself was wrong** — inherited from v1 §8: *"at 800 px wide, `1.5vw =
   12px`: it is the clamp minimum that a portrait tablet gets."* True at exactly 1.5vw. The
   flagged rules were `clamp(11px,1.6vw,14px)` and `clamp(12px,1.75vw,15px)`, which at 800 px
   resolve to **12.8 px and 14 px** — the coefficient binds and the minimum is unreachable.
   Replaced by `resolve_len()`, which computes all three dials at a target viewport
   (`--viewport`, default `800x1280`) and names the binding one in every finding. The rule is
   now stated in `SKILL.md` **§11.1** with both failure directions and their counts, because
   the skill text was as wrong as the code.
2. **`clamp()` was matched in any property.** `padding:clamp(10px,2.4vw,18px)` was reported as
   a type-size finding. Now gated on `font-size` only.
3. **Line numbers were shifted.** `strip_comments_css` replaced each comment with a single
   space, so a five-line banner comment swallowed four newlines and every subsequent line
   number drifted — reported 74/81/89/109/… against actual 103/110/118/138/…. Comments are now
   masked in place (non-newline characters → spaces), preserving line *and* column. Findings
   also now point at the offending declaration rather than the start of its rule.
4. **SVG `font-size` was judged on its declared value.** `.t-lbl` and `.t-part text` both
   carry `fill:`, so the skill's own SVG rule applies and declared ≠ painted. The static check
   now detects SVG by declaration or selector, **counts them and defers them to
   `measure_in_page.js`** with an explicit note, rather than guessing a scale it cannot know.

**And the precedence that would have contained it** is now written into
`references/verify.md` as its own section: *the browser measurement is the authority; the
static sweep only decides what is worth looking at.* Had that been stated, the 14 findings
would have been checked before being believed.

**Re-verification after the fix:**

- **`modules/m8/tasks`, same flags: exit 0, zero findings** — matching the browser. Plus a
  note that 3 SVG font-size declarations were deferred.
- **Proof the pass is real, not a silent skip.** All **58** `font-size` clamps in that
  stylesheet were resolved, **0 unresolved** — an unresolvable expression returns `None` and
  is not flagged, so a resolver that quietly failed would also have printed "ok". The
  resolution table reproduces the review's own numbers: `1.6vw → 12.80px`,
  `1.75vw → 14.00px`, both `clamp-coefficient`.
- **Line numbers verified against a purpose-built adversarial fixture** with a five-line
  banner comment and a two-line comment ahead of the violations: reported **exactly** lines
  6, 9 and 14. Property gate confirmed (a `padding:clamp` at line 10 not flagged), SVG
  deferral confirmed (lines 11 and 12 counted, not flagged), and a healthy
  `clamp(11px,1.6vw,14px)` at line 13 correctly silent.
- **`--viewport` changes results correctly**: `1.5vmin` → 12.00 px at 800x1280 vs **11.52 px**
  at 800x768; `min-height:2vh` → 25.60 px vs 15.36 px.
- **Resolver unit-checked** on `px/pt/rem/vw/vh/vmin/vmax`, all three clamp dials, and the
  never-guess cases (`calc()`, `em`, `%`, `var()` → `None`).

**`deadmarkup` was also scope-gated, for the same reason.** On the same real set it reported
**125 findings**, and the largest bucket was wrong in a way the floor bug had just taught me
to look for: a shared `../../../gb_nav.css`, pulled in automatically by the pages' own
`<link>`, whose classes are used by the app-shell `index.html` — which was not in scope.
A stylesheet outside the scanned tree also serves markup outside the scanned tree, so it
cannot be judged from there. Those are now **counted and skipped with a note** rather than
reported.

The remaining **114 were verified true**, not waved through:

- 104 of them are in the module's own 986-line `tasks.css`. Sampling eight against the
  *entire* course showed each class live in another module's markup and styled in 3–6
  stylesheets — i.e. genuinely dead in **this** copy. That is precisely the §13 defect the
  check exists to find, and the §14 per-module-copy drift.
- **Negative control:** `.rail`, `.count`, `.q-n` and `.mech`, all demonstrably used in this
  module's own markup, were **not** flagged; `.box`, used elsewhere but not here, was. So the
  check discriminates rather than flagging everything.
- Nothing was deleted. Deleting from one copy of a shared stylesheet is itself drift (§14),
  and this is course maintenance, not a task-screen defect.

Because a 114-line report still reads as an emergency, the check now prints a note above
that count explaining that this many findings is the **signature of a drifted per-module
copy**, and to confirm a sample against the whole course before deleting anything.

**`numbers` was also narrowed.** It flagged `newlyRight` in a shared task engine — an internal
per-submit counter that no record asks for and that correctly never paints. `right`,
`correct`, `count` and `tally` were removed from the name pattern, leaving `total`, `score`,
`points`, `marks`, `pct`, `percent`, `grade`. Loop counters are the normal way to write a
grader, and a noisy check gets ignored along with its true positives. The finding text now
opens with **"CANDIDATE — confirm before changing anything"** and the check prints a note
saying an internal counter that never paints is correct code — the previous phrasing said
"heuristic" but still read as an instruction.

## 7 · Cost pass (novikontas-token-economics, 2026-09-03)

Measured with the `novikontas-token-economics` skill's own `token_audit.py`, not by eye.
(That script lives in that skill, not in this bundle.)

**Always-on.** The description is the only always-on cost. Trimmed from **272 → 214 tokens**
(-21%) by cutting the trigger phrases that duplicated the task-type list and shortening the
boundary clause. **214 is over the 200 ceiling, and the reason is stated rather than skipped:**
this skill sits inside a family of near-misses — `course-module-ux` owns the module page,
`novikontas-presentations` owns the deck, the exercise skills own what a task assesses — and
a mis-trigger between them costs a whole wrong-lane run, far more than 14 tokens per
conversation. The clause naming `course-module-ux` is what buys that, and the task-type list
is what prevents under-triggering. For scale, the sibling `course-module-ux` carries 266.

**Bundle.** 24,213 tokens if nothing were lazy — up from 16,885 because the review round added
the clamp resolver, §11.1, the precedence section and this record. But **14,459 of that (60%)
can never enter context**: `MANIFEST.md` (7,010) is by convention never read at runtime, and
`check_task_pages.py` (7,449) is always phrased as *run*, never *see* — grepped to confirm no
"see `scripts/`" phrasing anywhere. `assets/` is copied into a course, not read. The review
round therefore added 7,328 tokens of which **5,884 (80%) is unreadable-by-design**.

**Worst-case single-mode load.** What can actually be read: `SKILL.md` 5,600 + `verify.md`
2,027 + `typed-input.md` 1,181 + `task-notes.md` 946 = **9,754 tokens**. The heaviest mode —
build a task that has typed input, then sign it off — reads all of it. The lightest, reviewing
a task's design only, reads the router alone at 5,600 (57%). Router share of the whole bundle
improved from 30% to 23%, because the round's weight went into a script and a maintainer file.

**The ~25% target does not apply here, and pretending otherwise would be the wrong fix.** That
target measures whether a lane split is real. This bundle has no lanes on purpose (§2): all
three candidate modes read the same standard, so a split would duplicate it or produce lanes
that are tables of contents. The honest number is the absolute one: **the entire standard for
the entire job is 9,754 tokens**, against `novikontas-presentations` at ~12,000 for one lane of
a 72,630-token bundle. The lazy loading that exists is genuine — a task with no text field
never pays the 1,181 for `typed-input.md`.

**Findings, in payoff order.** Description over budget: one, reason stated above. Loaded
unconditionally but needed by one mode only: none — the two references are both conditional
and both named with a "read when". Prose restating a declared-authority JSON file: N/A, this
bundle declares no JSON authority. Bulk reads not routed through a subagent: none; the skill
reads no knowledge base. Indexes read but never written back: none; the skill keeps no index.
Scripts the skill tells you to read: none, grep-confirmed.
