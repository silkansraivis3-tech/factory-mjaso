# Factory flow audit - 2026-11-10 (at 2.119.0, fixed in 2.120.0)

Asked by Aleksis: analyse the whole flow, find contradicting rules and keep the best, loosen rules that are too strict
on the AI, and say how courses get better, faster and cheaper. Three read-only audits (the laws, the build flow, the
screen / task / picture skills) found 22 + 29 + 34 contradictions, 39 over-strict rules and about 60 stale passages.
What was text was fixed in 2.120.0. What needs a ruling or real engineering is below.

## 1 · What 2.120.0 changed

- **One law table.** `plugin/skills/course-factory/SKILL.md` wins; every other file now says what it says. The rules
  2.118.0 removed were still printed as active in 40+ places (3D share, unasked 3D, "dense text needs a picture",
  content in parts, layout flip, "never a one-off SVG", photo row under every drawing). They are gone from the law
  documents, the build guides, the builder card, the workflow prompt and the five screen skills.
- **Rows reworded** so two laws no longer say opposite things: L9 against L11, L14 against L40, L23 against L61, L28
  against L66, L30 against the build with agents, L37 against "no picture quota", L46 against L67, L47 against the
  per-picture questions.
- **Loosened:** the self-check mix is a note when the task slide says why the subject has nothing to tap or operate
  (`"basic_why"`); a compiled text slide no longer fails the visual-first check; the builder is no longer told to
  answer L60 or to put a picture on every topic screen.
- **Cheaper:** the whole-course cross-check runs on Sonnet (it ran on the session model).

## 2 · Rulings still open (Raivis)

| # | The question | Today | Proposed |
|---|---|---|---|
| 1 | **Pictures of equipment.** 2.73.2 said "equipment too, first generated" and "never a photo to take". The table (L33) and the photo rule (L52) say equipment a trainee must recognise is never generated. | 2.120.0 keeps L33 / L52 and words `PHOTOS_TO_TAKE.md` as a list, never a stop or a question | confirm, or reverse L33 |
| 2 | **A generated 3D render under every drawing.** `media-and-tasks.json` `beside_drawing` places one unless the build sheet says `"no_picture"`; L57 says nothing goes under a drawing unasked | unchanged | make it opt-in, like the photo row |
| 3 | **The 3D and AI-picture proposals on the script review page** (`v_3d_propose`, `v_ai_propose`, up to two a module). L60 says no scene is proposed unasked | unchanged (notes) | remove `v_3d_propose`; keep `v_ai_propose` only for a slide whose picture slot is empty |
| 4 | **60 % of the old course's words is a must-fix** (L71, `o_thinner`). It forces a wordy rebuild of a wordy old course, against "fewer words" | unchanged | judge the old slide's points kept, not its word count; under 60 % a note |
| 5 | **A figure that looks like one of the last five fails the compile** (2.115.0) while a slide's look repeating is a note (L62) | unchanged | a note, with the figure it resembles |
| 6 | **The hands-on question in every module is a must-fix**, also for law and management modules | unchanged | the same `"basic_why"` exception |
| 7 | **Instructor notes over 50 words are a must-fix** | unchanged | a note; under 10 stays a must-fix |
| 8 | **kit or kit2d for a new ship-system drawing** - the skills now say kit for machinery and systems, kit2d for ideas, sequences and numbers | text only | confirm |

## 3 · Faster and cheaper (not built)

1. **The walk review is outside the whole-course workflow.** `build_course.js` has no walk step, and a parallel build
   (`--no-course-pages`) never reaches the gate in `build_module.py`, so every module of a workflow build is refused at
   upload until the lead session walks it by hand. Add a walk judge beside QA, figures and 3D; its fails join the one
   fix round.
2. **Two reviews look at the same slides.** The sheet review (Quickstart step 5, `REVIEW_PROMPT.md`) and the walk
   review both judge every slide, and a kit figure is judged up to four times (drawing check, figure review, sheets,
   walk). Keep the walk for the deck and the sheets for the task pages only.
3. **The walk loop has no end and one hash.** "Until verify says OK" has no cap, and one whole-deck hash makes every
   slide stale after a one-slide fix. A hash per slide, two rounds at most, the rest on the operator's list.
4. **QA builds the module the builder has just built** (`build_module.py --no-fix`, about 97 s and a model turn a
   module). Read the builder's answer file and build again only when it is older than the build sheet.
5. **The final assessment's builder loads the whole skill** (about 12,000 tokens a turn) and reviews itself. Give it
   the builder card and the judges, like every other module.
6. **`compile/GUIDE.md` is 86 KB and still the entry point for a single-session build.** Reading the guides cost IGF
   M02's builder $19.6 of $25. Split it into a 70-line Quickstart and a reference nobody reads whole.
7. **Twelve sign-off commands and QA's second set of checks are separate model turns.** They are file checks of a few
   seconds: run them inside `build_module.py` or one `verify.py`.
8. **Approvals one at a time.** `content_script.py approve --modules 1-21 --by <name>` after the operator has read
   them is still their own act and is one turn, not 21; the instructor-led approval fits the same pop-up.
9. **Four copies of every law.** SKILL table, `owner-decisions.md`, `laws-in-full.md`, `docs/FACTORY_LAWS.md`. Every
   rules release has to change four files and misses some. Keep the table and one reference file; generate
   `FACTORY_LAWS.md` from the table.
10. **`knowledge/build-order.json` stops at 2026-10-16.** It has no Phase A / B, judges, walk review, expert pedagogy
    step or instructor-led step, and it is called the authority.

## 4 · Better courses (not built)

1. **No check of the wrong answers at all.** Nothing looks for the right option being the longest, near-duplicate
   options, "all of the above", or a clue word only in the right answer. These are cheap script checks.
2. **Nothing checks that a task tests its outcome.** Only that a `"sub_ilo"` tag is there. Compare the outcome verb's
   level (`bloom.json`) with the highest question level on it; two levels below is a must-fix.
3. **"Taught before asked" is a word count** - 60 % of the answer's word stems on earlier slides. Let the fact-checker
   pair each question with the line that teaches it.
4. **Feedback is checked only for not giving the answer away.** Require a reason on every wrong choice of a quick
   question and flag the same reason used across a set.
5. **The walk review covers the deck only, and anyone can sign it.** The task pages are the graded part; the builder
   can sign its own work. Walk the task pages too and refuse the builder's own signature.
6. **A drawing a seafarer would call wrong can ship.** Figure leftovers go on the operator's list and the upload does
   not look at it. Refuse the upload while a BROKEN figure has no "accept".
7. **A claim the knowledge base search did not find is cut in an unattended build.** A gap in the knowledge base
   becomes a gap in the teaching. Write it to `OPEN_EXPERT_QUESTIONS.md` instead.
8. **`course-visuals/decide/GUIDE.md` puts an explanation and its picture on separate screens** as good practice; a
   trainee then holds one in mind to read the other. Explanation and picture belong on one screen.

## 5 · Found on main, not caused by 2.120.0

- `compile/scripts/test_task_engine.py`: "each tappable area covers its drawn part, at least 56 px" fails for parts
  `mv`, `tk`, `pp` at both tablet sizes.
- `course-module-ui/scripts/test_design_system.py`: class `lt-ans-under` of `gb_upgrade.css` is missing from
  `references/vocabulary.md`.
- `course-visuals/kit/scripts/test_patterns.py`: `fuel_space_access.kit.json` in the narrow column at 1024 x 768 prints a
  label over its leader line.
- There is no command that runs all 93 test files; a run takes over an hour one by one, and
  `test_build_module.py`'s "at once" timing check fails when another test run shares the computer.
