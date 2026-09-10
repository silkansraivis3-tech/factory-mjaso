# MANIFEST — course-module-ux

**v1 (2026-09-03) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

Maintainer file. **Never read at runtime.** It exists so a session six months from now can pick
this bundle up cold, including a session with no memory of why any of it is the way it is.

---

## 1 · Design principles — the deliberate tradeoffs

**a · Course-agnostic by construction, not by intention.** The owner's brief was *"i will in
another claude code use on other study program"*. So: no absolute paths anywhere, no dependence
on this machine's folder layout, no course name in any guide, and the engine files bundled inside
the bundle rather than referenced from a course tree. Every real-world number that appears is
labelled as *from one project*, never as *the* course. Selectors and thresholds live in a CONFIG
block at the top of each script, above the logic, so porting is an edit to a named block rather
than a hunt.

The one thing that is **not** brand-agnostic: `assets/gb_run.css` carries Novikontas colour
literals inline rather than as custom properties. See Known gaps #1.

**b · Four lanes, because there are four modes that never run together.** The suggested split
was accepted with one change of emphasis. Justification, mode by mode:

| Lane | Why it is its own lane |
|---|---|
| `build/` | Building is additive and forward-looking. It never needs to know what the old model was. |
| `convert/` | Converting is almost entirely *removal*, and it needs the superseded patterns named. A builder who reads it learns three defects they would otherwise never have written. |
| `runscript/` | Runs against a finished deck, by anyone, at any time, including someone who did not build it. Nothing else in the bundle is needed to run it. |
| `measure/` | The only lane that is mostly *code*, and the only one used on artefacts this skill did not produce. |

`convert/` deliberately points forward into `build/knowledge/*.json` and `build/GUIDE.md` §7–8
rather than restating them. That is the one cross-lane read in the bundle and it is stated in
`convert/GUIDE.md` §3 at the step where it happens, so it is a sequenced read, not a co-load.

**c · The measurement discipline is scripts first, prose second.** Most of it is checkable by
code, so it is: static checks with exit codes (`check_static.py`), four browser probes with
single-line verdicts and `window.__auditExit`, and a fresh-port server that prints its own PID.
The prose in `measure/GUIDE.md` exists only to say *which* probe to trust for *what*, and why
running one of a pair is worthless.

**d · `check_static.py selftest` — the checker checks itself.** A checker that returns "clean"
on every input is worse than no checker, because it produces a signed-off report. The bundle
ships a deliberately broken fixture and a selftest that fails if the checks come back clean on
it. This came directly from watching the `slide-links` check pass on four real modules and not
being able to tell, from that alone, whether it worked.

**e · Traps and the floor are JSON, and the guides point at them.** They are decision data that
scripts also read, so prose restating them would create two versions of the truth. `floor.json`
is genuinely read by `check_static.py`, not just declared as authority.

**f · The gate is the screen inventory table.** One module went 6 screens → 18. Approving a
table row is free; rebuilding fourteen screens is not.

---

## 2 · Architecture — the tree, matching disk

```
course-module-ux/
├── SKILL.md                              router: architecture, mode table, seven laws, gate, markers
├── MANIFEST.md                           this file — never read at runtime
├── templates/
│   └── DELIVERY_NOTES.md                 companion file; every honesty marker lands here
├── assets/
│   ├── gb_run.js                         the step runner + return bar engine (course-agnostic)
│   └── gb_run.css                        its stylesheet (Novikontas brand literals — gap #1)
├── build/
│   ├── GUIDE.md                          building a module page; budgets; record engines
│   └── knowledge/
│       ├── screen-kinds.json             AUTHORITY: screen kinds, markup contract, runner shape
│       └── audience-split.json           AUTHORITY: per-item routing, screen vs instructor cue
├── convert/
│   └── GUIDE.md                          off the chained model; the three superseded patterns
├── runscript/
│   ├── GUIDE.md                          derive the instructor running order; the three traps
│   └── scripts/
│       └── gen_run_script.py             RUN IT. exit 0 clean / 1 findings / 2 usage
└── measure/
    ├── GUIDE.md                          what to trust, in what order, and why
    ├── knowledge/
    │   ├── traps.json                    AUTHORITY: the thirteen measurement traps
    │   └── floor.json                    AUTHORITY: the sign-off floor; read by check_static.py
    └── scripts/
        ├── check_static.py               RUN IT. subcommands + selftest
        ├── serve_fresh.py                RUN IT. fresh unused port, prints its own PID
        ├── audit_deck.js                 browser probe: text size, contrast, controls, fill
        ├── audit_collide.js              browser probe: collisions and overlaps
        ├── audit_drive.js                browser probe: drives the deck screen by screen
        ├── audit_opacity.js              browser probe: proves what you measure is visible
        └── fixtures/
            └── control_page.html         deliberately broken; the selftest's input
```

`templates/DELIVERY_NOTES.md` deliberately carries **no** version header: it is an artefact the
operator fills in and copies next to a module, not a guide, and stamping this skill's version
into a file that ships with a course would go stale in the course rather than in the bundle.

`assets/` sits at bundle root rather than under a lane because both `build/` and `convert/`
copy from it. It is two files and it is never read into context — only copied — so the cost of
the exception is zero.

---

## 3 · Provenance — carried, new, and deliberately not copied

### The dedup check

Done before drafting, by the caller: installed skills listed, descriptions read, and the four
plausible overlaps grepped — `gas-basic-module-ux`, `course-task-ux`,
`novikontas-presentations`, `novikontas-course-start-page`. Result, carried here unchanged:

| Concept | Already lives in | Disposition |
|---|---|---|
| Compactness law, navigate-don't-narrate, record engines, paperless rules, tablet interface rules, visual-language "do not restyle" | `gas-basic-module-ux` §§1, 3–8 | **Carried** — rewritten in this skill's own words for the new architecture. These survive the change. |
| Next-Next walk, geometry per viewport, touch targets, link/asset check, paper sweep | `gas-basic-module-ux/reference/QA_CHECKLIST.md` §§0, 1, 2, 4, 5, 8 | **Carried** — and turned from copy-paste console snippets into scripts with exit codes, plus the measurement traps that were absent from it |
| Trainee task screens: what a task may contain, answer mechanics, two-stage tap, photographs, the task floor | `course-task-ux` | **NOT copied — pointed at.** Named in the router's boundary table. That skill was being extended in parallel and its own description now points back here, so the boundary is mutual. |
| Deck template engine, House Rules, copy budgets, `build.py` | `novikontas-presentations` | **NOT copied — pointed at**, in the router's boundary table |
| Offline start page / delivery package / "which file do I open first" | `novikontas-course-start-page` | **NOT copied — pointed at**, in the router's boundary table |
| Exercise design, course intake, pedagogy, ILOs | the `novikontas-*` family | **NOT copied — pointed at**, in the router's boundary table |

### Per item in this bundle

| Item | Source | Disposition |
|---|---|---|
| `SKILL.md` laws 3–7 | old skill §§1, 3, 4, 6, 7, 8 | **Carried**, rewritten and compressed. Law 1 (audience) and law 2 (`data-cue`) are **New**. |
| `SKILL.md` architecture section | owner instructions, verbatim, dated today | **New** |
| `SKILL.md` honesty markers | `novikontas-skill-conventions` §6 | **Carried** as the defined set, routed into `templates/DELIVERY_NOTES.md` §2 |
| `SKILL.md` gate | conventions §6 | **Carried**, with this skill's own expensive step named |
| `build/GUIDE.md` §§1–2 (timetable first, everything becomes a screen) | the 90-missing-minutes finding and the real screen counts | **New** |
| `build/GUIDE.md` §7 budgets | old skill §3 | **Carried** verbatim in substance, trimmed |
| `build/GUIDE.md` §8 record engines | old skill §5 | **Carried**, de-parameterised: the three engines are described by *what produced the result* rather than by their file names, since only `gb_run.*` is bundled |
| `build/GUIDE.md` §§9–10 (never animate into visibility; read the console) | project memory + two real bugs | **New** |
| `build/knowledge/screen-kinds.json` | the real markup contract, read off four built modules | **New** |
| `build/knowledge/audience-split.json` | the owner's audience instruction plus the items actually moved on this project | **New** |
| `convert/GUIDE.md` §0 | the three superseded sections of the old skill | **New** — the old skill taught these as correct; naming them as defects is the point of the rewrite |
| `convert/GUIDE.md` §1 the two phases | the owner's correction of 2026-09-03 plus the preserved pre-cut decks | **New** — the single most important thing in the lane, and it was missing from the original brief |
| `convert/GUIDE.md` §3 order | old skill §11 | **Carried**, re-ordered for one page and with the chain-stripping step added |
| `convert/GUIDE.md` §5 three buckets | old skill's QA §9 last bullet | **Carried**, promoted from a checkbox to its own section |
| `runscript/` (whole lane) | — | **New**. Nothing like it existed. |
| `measure/knowledge/traps.json` | this project's audit sessions (13 traps) plus the probe-genericisation pass in this session (5 more: `selector-matches-nothing`, `chrome-selectors-not-discoverable`, `collide-not-repeatable`, `sibling-painted-background`, `backgrounded-tab-throttling`) | **New**, 18 traps. The caller grepped: zero hits anywhere for the first three. |
| `measure/knowledge/floor.json` | old skill §12 + QA §§4, 5 | **Carried** and made machine-readable |
| `measure/scripts/check_static.py` | QA §§1, 2, 8 as prose snippets | **Carried** in intent, **New** as code — the `slide-links` carve and the `check-screen` and `mins` checks did not exist |
| `measure/scripts/serve_fresh.py` | QA §0's `python -m http.server` one-liner | **New** — the fresh-port and kill-by-PID rules were prose nowhere enforced |
| `measure/scripts/audit_*.js` | `_claude_working_area/audit_*.js` on this project | **Carried and genericised** — see §5 gap #2 for the honest verdict on each |
| `assets/gb_run.js`, `gb_run.css` | old skill `assets/` | **Carried**, header comments de-branded; behaviour untouched |
| `templates/DELIVERY_NOTES.md` | conventions §6 companion-file rule | **New** — the old skill shipped no companion file at all |

### Deliberately NOT bundled from the old skill

`gb_forms.*`, `gb_observe.*`, `gb_phase.*`, `gb_roster.js`, `gb_score.*` — seven engine files,
~85 KB. Reason: `gb_phase` paged a *practical document*, and practicals are screens now, so it
has no job in this architecture. The four record engines are for the instructor's own recording
device, which is a different artefact from the module page and is arguably `course-task-ux`'s
neighbour rather than this skill's. `build/GUIDE.md` §8 therefore teaches **how to choose** a
record engine and what the non-negotiable rules are, without shipping the code. The files remain
in `gas-basic-module-ux/assets/` as the only copies, and the stub says so.

---

## 4 · Conflicts found and resolved

| Conflict | Resolution |
|---|---|
| The old skill's §2 taught the hand-over chain as the target state, quoting the owner approvingly. The current standard deletes it. | The **course as built** wins over the old skill's text. Modules on the new architecture were re-grepped in this session: zero surviving `next:` / `gb-finish` / `data-gbrun-to` in the four converted modules. The old text is named as superseded in `convert/GUIDE.md` §0 rather than silently dropped. |
| The old skill said "four to six steps is a module. Nine is a filing cabinet." The new architecture says about **two**. | Two. The old number counted *artefacts the instructor opens*, and there is now one. |
| The old skill's QA §0 opened with `python -m http.server 8731` — a fixed port. The stale-cache trap says fresh port every time. | Fresh port. `serve_fresh.py` enforces it and remembers which ports it has used. |
| `skill-creator` wants an `evals/` directory and a test-and-iterate loop; `novikontas-skill-conventions` wants router + lanes + MANIFEST and says it wins on shape. | Conventions won on shape, so there is no `evals/` in the bundle. See Known gaps #4 — the eval loop was not run, and that is a real gap, not a decision that it is unnecessary. |
| I wrote a trap saying `kill <pid>` does not work on Windows and `taskkill` is needed. The owner tested plain `kill` and it freed the port. | The owner's test wins; my trap was a false generalisation from one observation, and **a false trap in a portable skill is worse than a missing one** — the next person adds `taskkill` to a script on a platform that may not have it. Rewritten as the durable rule: *confirm a stop by probing the port, never by trusting the exit code of whatever stopped it.* The narrow mechanism I actually saw (a later shell cannot see a PID from an earlier tool-call shell: `kill: (25380) - No such process`, exit 1, port still bound) is recorded as the mechanism, with `taskkill` demoted to a fallback. |
| I marked **29 → 8** and **38 → 6** `[VERIFY]`, reasoning they must be file counts because a module cannot both shrink and grow. | They are real screen counts; the history has two phases. Verified on disk myself. My reasoning was wrong because the brief compressed two separate passes into one table — which is why the two-phase shape is now taught in `convert/GUIDE.md` §1 rather than left implicit. |
| `data-mins` was documented as an attribute on the section; on disk it is on a timer element **inside** the slide. | Both. The generator collects it from either, and `screen-kinds.json` says so. Found by running the generator against four real modules, not by reading. |

---

## 5 · Known gaps / before this goes live

**1 · `assets/gb_run.css` is brand-coupled, not course-coupled.** It carries ~37 distinct
Novikontas colour literals inline rather than as custom properties. Course-agnostic it is;
brand-agnostic it is not. For a non-Novikontas course the six load-bearing values to swap are
`#0A2463` (navy), `#0A182E`/`#06182b` (deep navy), `#2EB6F8` (screen blue), `#E9A51E` (amber,
accent only, never body text), `#011111` (body ink), `#fff`. **Not converted to custom
properties in this session** because a blind palette refactor of a working engine is exactly the
kind of restyle law 7 warns against. Would be verified by loading a module page before and after
and diffing screenshots.

**2 · The four browser probes: portability is per probe, not uniform, and one has a gap that
fails silently.** They were genericised from this project's working copies — CONFIG blocks
hoisted, ES5 kept (explicit Promise chains, since `async` is ES2017; `Promise` itself remains a
runtime dependency), and the safety guards added: viewport abort, a ≥520 ms settle floor that
*clamps* any lower CONFIG value, `display:none`-only filtering, `.frag` reveal, and `offset*`
over `getBoundingClientRect` in `audit_deck`.

The couplings that were actually found are **deck-template ids and classes, not course
content** — nothing in any of the four is named after a course. That sets the honest ceiling:
they port freely across decks built from the same template and need a CONFIG edit, not code, for
a foreign one. Per probe: `audit_deck` and `audit_opacity` **portable**; `audit_collide`
**portable with one gap** (check 3 needs the chrome selectors set or it reports an unearned
pass — recorded as `traps.json#chrome-selectors-not-discoverable`); `audit_drive` **portable in
form, coupled in substance**, because it encodes a navigation model CONFIG cannot abstract.

**Verified in this session**, on a real 14-screen module served on a fresh port:
all four parse (`new Function`, no `node` on this machine); all four load, run and return
`VERDICT: PASS` on a clean deck with `__auditExit = 0`; the 0×0-viewport abort genuinely fired
during genericisation; and a **negative control** — one injected sub-floor low-contrast paragraph
and one injected `<a href>` inside a slide — produced `VERDICT: FAIL n=6` with
`{low:2, small:2, tap:2}`, so they are discriminating rather than rubber-stamping. ES5-safety was
independently confirmed by executing all four under Windows JScript.

**Parity caveat.** During genericisation the rewrites were checked byte-identical to the
originals on totals, medians and fills. After that, `audit_deck.js` was **deliberately patched
here** to count three defects it previously reported but did not count — overfill, links inside
slides, document h-scroll — because a deck whose only fault was one of them printed
`VERDICT: PASS`. That was reproduced (one injected link, verdict stayed PASS) and then fixed and
re-verified. So `audit_deck.js` is intentionally no longer at parity on the *failure count*.
Running it against the real module immediately surfaced three genuine overfilled screens at
103 %, 103 % and 101 %.

**Still unverified**: `audit_collide`'s check 3 on a foreign deck, and every probe at the three
non-default viewports in `floor.json`. What would verify them: run the four at 1366×768,
1024×768, 800×1280 and 360×740, reloading after each resize.

**3 · The description is 206 tokens, over the 200 budget.** The stated reason: this skill sits
between two near-misses that share its vocabulary — `course-task-ux` (which owns "module check",
"task", "tablet") and `novikontas-presentations` (which owns "deck", "slides"). The boundary
clauses and the trigger phrasings are what keep it from firing on their work and from failing to
fire on its own. An under-triggering skill costs its whole body in work done badly without it.
Cut from 266 → 218 → 206; further cuts would come out of the boundary clauses.

**4 · No eval loop was run.** `skill-creator`'s test-and-iterate loop (test prompts, baseline
runs, grading, the eval viewer) was not executed — this was a single-session rewrite against a
detailed brief. What would verify triggering: 20 trigger-eval queries with the near-misses being
`course-task-ux` and `novikontas-presentations` work, run through `run_loop.py`. What would
verify the guides: three test prompts — build a module from a timetable, convert an old chained
module, and audit a deck — run with and without the skill.

**5 · CLOSED 2026-09-03 — the two odd before/after numbers were real screen counts.** I had
refused to assert **29 → 8** and **38 → 6** and marked them `[VERIFY: …]`, guessing they counted
files. They do not. The owner supplied the missing context: the history has **two phases** — a
cut back to the architecture's own decision (M4 29→8, M5 38→6, M6 34→8, M7 28→10), then weeks
later the absorption of the practicals into the deck (M5 6→18, M6 8→14, M7 10→14). I re-counted
the phase-1 "before" figures myself off the preserved pre-cut decks at
`course/_full_decks_2026-09-02/` — `<section class="slide">` gives 29, 38, 34, 28 — so all of it
is verified on disk. The markers are gone and `convert/GUIDE.md` §1 now teaches the two-phase
shape, because **doing only phase 1 is the 90-minutes-missing defect**.

**6 · The three superseded patterns are asserted from the caller's brief plus one grep.** I
confirmed in this session that the four modules on the new architecture contain zero `next:`,
`gb-finish` or `data-gbrun-to`, and that `gb_run.js` documents the counter consequence in its
own source at lines ~156–165. I did **not** re-find the five practical pages that carried the
bug — they were already fixed before this session. The claim "five pages across three modules"
is therefore reported, not re-derived.

**7a · `node` is not installed on this machine.** Verified (`which node` → nothing). That is not
a gap in the bundle but it is why `traps.json#console-after-scripted-edit` insists on the browser
console: there is no offline JavaScript syntax check available here. The probes are syntax-checked
by `new Function()` — in the browser, and offline via `cscript //E:JScript`. All four were re-checked that way after the last scripted edit to `audit_deck.js`, which is the rule applying to itself.

**7 · `check_static.py paper` is a candidate-finder, not a verdict.** It cannot tell a print
button from an instruction to print. It says so in its own output line. A human closes each hit.

**8 · No real-run companion file exists yet.** `templates/DELIVERY_NOTES.md` §7 is the feedback
channel and it has never been filled in. At the next revision, read it first.

---

## 6 · Cost pass — `novikontas-token-economics`, run 2026-09-03

### Always-on

| Skill | Description tokens |
|---|---|
| `course-task-ux` | 214 |
| **`course-module-ux`** | **206** |
| `gas-basic-module-ux` (stub) | 57 |
| **total, every conversation** | **477** |

206 is 6 over the 200 budget; the reason is stated in gap #3. The stub replaced a 57-token
description that used to be a full triggering one — the supersede *reduced* always-on cost.

### Bundle

| | |
|---|---|
| Counted full load | **33,832 tokens** |
| Router (`SKILL.md`) | **2,396 — 7 %** |
| Largest single file | `MANIFEST.md` 6,030 (18 %) — **never read at runtime**, which is the right place for the biggest file |
| Not counted by the audit | the four probes, **71 KB ≈ 17.8k tokens**, plus `assets/gb_run.*`. Neither is ever read into context — the probes are loaded by the browser, the engine is copied |

By lane: `measure` 11,842 (35 %) · root 8,426 (25 %) · `build` 5,756 (17 %) · `runscript`
4,596 (14 %) · `convert` 2,320 (7 %) · `templates` 892 (3 %).

### Worst-case single-mode read load

| Mode | Reads | Tokens | vs counted full load |
|---|---|---|---|
| Run script | router + `runscript/GUIDE.md` | **3,838** | 11 % |
| Measure | router + guide + `traps.json` + `floor.json` + notes | **10,240** | 30 % |
| Build | router + guide + both knowledge files + notes | **9,048** | 27 % |
| **Convert** | the above two, **sequenced** — its own guide, then `build/`'s knowledge and §7–8, then `measure/` at step 9 | **~18,300** | **54 %** |

Three of the four modes are at or under the ~27–30 % mark. **Convert is over it, and that is a
real finding rather than a defect I can design away**: a conversion legitimately does build work
and then measurement work, so it reads three lanes. What makes it acceptable is that the reads
are **sequenced, not co-loaded** — `convert/GUIDE.md` names each forward read at the numbered
step where it happens (step 4 for the knowledge files, step 8 for the budgets, step 9 for
measurement), so a conversion abandoned after step 3 has paid for none of it. Against the true
bundle size including the probes (~52k) convert is 35 %.

### Findings, in payoff order

1. **Description 6 tokens over budget** — reason stated (gap #3), not skipped.
2. **Nothing loads unconditionally that only one mode needs.** The router reads no lane and no
   knowledge file; it names them in a table with a read-when column.
3. **No prose restates a declared-authority JSON.** Checked by grep: `screen-kinds.json`'s
   markup contract, kind rules and runner shape appear nowhere in prose; `audience-split.json`'s
   routing table appears nowhere in prose (the guides restate only the *rule* and the *test*, not
   the table); `floor.json`'s thresholds appear in `measure/GUIDE.md` only as the two figures
   the narrative needs (12.5 px, 100 % fill) and it is `check_static.py` that actually reads the
   file; `traps.json`'s traps are named by id in the guide, with the mechanism only where the
   narrative needs it (the settle and the clamp dials).
4. **No bulk reads in the bundle**, and the one bulk read this session needed — genericising
   ~34 KB of probe source — went through a subagent, which returned a compact verdict rather
   than the code.
5. **No index is read-but-never-written.** The bundle ships no lookup index. `serve_fresh.py`
   writes back to its used-ports state file, which is the only persistent state anywhere.
6. **Every script is phrased "run it", never "see it".** `measure/GUIDE.md` and
   `runscript/GUIDE.md` both say run, with the exit-code table, and the one place that tells you
   to *read* anything in a script is the CONFIG block — which is the point of hoisting it.
