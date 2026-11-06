# IGF Basic built end to end by Course Factory 2.56.0 - review (2026-10-20/21)

**What was done.** The whole IGF Basic course (M01-M15 + the final, module16) was built **from scratch** by the
factory's whole-course workflow, unattended, into a separate folder: `Desktop\IGF_course_2.56.0\course`. The real course
in `Desktop\Kursi\` was only read. Kept from the real course: the approved scripts (words, ILOs), the architecture and
ILO map, the knowledge base, and each module's photos. Removed on purpose: every build sheet, figure spec and built page,
so the factory had to make all of it again. The Gas Library was used through a copy, and the real library on Drive is
unchanged (checked against a fingerprint taken before the build). Factory = `integrate/2026-10-20` (2.56.0: the build-loop fixes, the output
defects, the Gas Library, the realistic kit L62, Raivis's layout templates L61, today's merge fixes), all 45 test files
passing. Baseline = `IGF_course_2.56.0\BASELINE_original_build.md` (how the original was built, from its own records).

## Verdict in one line

**Mostly better and far less hands-on.** One unattended run built the whole course, on Raivis's new templates, for about
$110-140. After assembly, 13 of the 16 modules pass every check, and the course packages for the classroom (16 modules,
514 trainee files). It is **not yet faster per module** than a good single-module session, because 75-90 % of build time is
waiting on the check scripts. It is also **not finished**: M15 stopped early, the final fails on a factory bug, and M03 is
one audit short.

## The numbers

| | Original build (records) | 2.56.0 rebuild |
|---|---|---|
| How | M01-M03 hand-built pilots, then M04-M06 in single sessions, M07-M15 + the final overnight on 10-16; corrections over 10-14 to 10-19 | one unattended workflow, 15 modules in waves of 3, then the final, assembly, cross-check |
| Operator time | several days of reviews; 281 audit corrections to M01-M03 alone | none during the build; 105 POLISH notes listed for you, plus 3 open items |
| Wall clock | ≥ 322 min recorded (M01-M03, M05 and the correction passes not recorded) | **6 h 21 min** for everything, incl. 8 3D scenes |
| Model | Opus 5.5 sessions + Sonnet subagents | Sonnet 5.5 for every agent (builder and QA at medium effort) |
| Cost | not recorded | **≈ $107 in tokens + output tokens** (under-recorded in the transcripts) ≈ **$110-140**; median **$4.60 per module**; the same tokens on Opus 5.5 ≈ $138 + output at double the price |
| build runs per module | M04 18, M06 10, M10 4, others 1-3 (as drafts) | median ~8, range 1-17 (M11 17, M07 16, M14 15) |
| Pass after assembly | - | **13 / 16** (M03 audits, M15 unfinished, final factory bug) |
| Re-checking the whole course | - | **11 min** for all 16 modules on a quiet PC (15-83 s each) |

Cost per module, build + QA: M01 $12.6, M02 $25.8, M03 $12.6 (the first wave, see below), then M04-M15 $1.6-9.5. Final $1.0,
cross-check $2.8, assembly + gate $0.25. Prices: Sonnet 5.5 $2 in / $10 out per MTok, cache read $0.20, cache write ~$2.50.

**Where the time went.** Of each builder's time, 70-90 % was the PC running `build_module.py` (figures, compile, browser
audits) and 10-30 % was the model. The first wave (M01-M03, 126-148 min each) spent 110-122 min **each** waiting on scripts.
It ran while the browser-pool session was testing on the same PC (the CPU was pinned). Later waves ran 6-82 min per module.

## Is it the same quality, or better?

Same approved words: 196 slides, as the original. The instructor and trainee word checks match on 14 of 16 modules.

| | Original | 2.56.0 |
|---|---|---|
| Slides on the owner's layout templates (L61: 55/45 split, a visual beside dense text, no 3 text-only slides in a row) | 0 | **every slide** (4-6 templates per module) |
| Real photos on slides | 58 | 58 (different mix) |
| Real photos in trainee tasks | 6 | 7 |
| Photos from the Gas Library | 0 | **19** |
| AI pictures shown to trainees | 9 | **1** (unused files are no longer shipped; library AI pictures of equipment are blocked) |
| 3D slides | 9 | 8 (M03's scene not rebuilt) |
| One visual style across modules | - | **yes**: 11 shared stylesheets and 8 scripts byte-identical in all 16 modules |
| Equipment drawings | flat | realistic materials (L62) |
| Instructor notes promising 3D or tapping that the slide cannot do | present | caught and fixed via propose/apply |
| Package for the classroom | - | 16 modules, 514 trainee files, no module-level problem |

**Better:** the owner's layout rules everywhere; fewer AI pictures; library photos; one style; realistic equipment; notes
that match the slide; dense text never without a picture; every rebuild checked against the approved words.

**The same, and still short of your rules:**
- **Real photos in tasks:** 7 in the whole course. The factory now lists, after each build, which task questions a real
  photo could carry (M03: q06, q07), but the builders did not act on it.
- **Photos still to take** (`PHOTOS_TO_TAKE.md`): M01 9, M03 24, and so on. The spaces themselves (tank connection
  space, fuel preparation room, vent mast) exist only as drawings.
- **Learner-active time:** M01 13 of 40 min (32 %) against the 80 % target. This is the owner's open decision.

**Worse, or weaker:**
- M03 lost its 3D scene.
- M03's builder flagged four library photos that only roughly fit their slide: a ferry, not a bunkering; oil-tanker
  loading arms, not an LNG berth. The library's matching takes "close" as found.
- The visual review was done by the builders themselves on sheets the build never promoted (see bug 1). The final's
  builder read 18 of 92 sheets.

## What went wrong in this run (all factory, all fixable)

1. **No module ever saw PASS during the build.** `build_module.py --no-course-pages` leaves out the package findings
   about course pages and other modules, but not two more kinds: the empty Google Drive sync folders
   (`.tmp.drivedownload` / `.tmp.driveupload`) that came along from `Kursi`, and the importer's "course id / title"
   errors before assembly. So every module ended "FAIL - course package". Its review sheets were never promoted, and the
   builders reviewed unpromoted sheets. After assembly and removing the Drive folders, 13 pass.
2. **A builder can stop while its own build runs in the background.** M15's agent ended its turn "waiting on the build",
   so the module was never finished: figures fail (small text 10.5 px, a valve outside its plate), and a 3D hint is not
   in the approved words. The workflow took its report as done.
3. **`build_module.py --module final`** runs the word checks on `modules\mfinal` (it does not exist). The final's words
   match when the checks are pointed at module16 by hand.
4. **Nothing was saved back to the Gas Library**: 0 pictures, 0 facts, 0 terms. Pictures came from the library, but the
   save-back step for facts and terms found while writing is never prompted in a build of approved scripts.
5. **The ILO map is stale** (written 10-19; 186 of 268 rows still say "planned - module not built"). The practical
   minutes (M09 1.5 h, M13 2 h ...) are shown nowhere. LEL and LFL are both used for the same limit.

## Where to improve next (ranked by gain for the effort)

| # | Change | Gain | Effort |
|---|---|---|---|
| 1 | **Merge 2.57.0** (browser-pool session, already committed): one pool of hidden browsers for the PC; a rebuild re-checks only changed slides and pages | attacks the 70-90 % waiting directly; no more 99 % CPU when builds overlap | merge + measure |
| 2 | **Fix bug 1**: parallel-mode package check leaves out sync-tool folders (`.tmp.drive*`, `desktop.ini`) and pre-assembly importer id/title errors | every module reaches PASS and promotes its review sheets | S |
| 3 | **The workflow checks each builder's last line**: no PASS = send it back to continue; and a rule that a builder never ends with its build in the background | no half-built module (M15) | S |
| 4 | **Fix bug 3** (`--module final` word checks) | the final passes | S |
| 5 | **Assembly before cross-check inside `build_course.js`** (worked in this run's harness), plus `ilo_map.py refresh` after assembly | the cross-check judges the real course; ILO map current | S |
| 6 | **A separate review agent per module** (Sonnet; haiku after a side-by-side) on promoted sheets | an independent look instead of a self-review; all sheets read | M |
| 7 | **Real photos in tasks by default**: when the post-build note names a fitting photo, the builder uses it unless declined | more real photos in tasks (your rule) | S-M |
| 8 | **Library match quality**: say "close, not exact" for pictures like M03's ferry, so the builder or you decide | fewer near-miss photos | S |
| 9 | **Save-back as a build step**: facts and terms with sources found while building go to the library inbox | the library grows with each course | S |
| 10 | **Owner decisions still open**: learner-active 80 %, the graded module check (L27), LEL vs LFL, task codes unique across modules, practical minutes on the course page | content quality | Raivis |

## What I would do next

1. Merge 2.57.0 and fix bugs 1-4 (one small branch), then rebuild **only M15 and the final** and re-run M03's audit fix.
   Expect a fully passing course.
2. Rebuild the whole course again overnight on a PC nothing else is using: the clean time per module with the browser pool.
3. Push 2.56.0 (+ fixes) to `main` with your yes - it now contains Raivis's templates, so tell him what changed (this file
   and `_claude/CONTEXT.md` 2.53.0-2.56.0).

*Data: workflow `wf_67c0714c-301` (34 agents, 6.67 M subagent tokens, 2,635 tool calls), per-module re-check after
assembly, content counts from the built folders, baseline from the original course's own records. Every number from a
transcript is a count of what was recorded. Output tokens are under-recorded, so the dollar figure is a lower bound plus an estimate.*
