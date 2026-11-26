# History of the numbers in the knowledge files

Why a number is what it is, moved out of the JSON so the files agents read hold rules and values only. Nothing here is
read by a script. Each entry names the file and the key path it came from.

## theory-rules.json

### `_authority`
How much theory a module carries, and how much must be taught before a trainee is asked anything (L36). The owner,
2026-09-30: 'slide text is too small ... with that low info can [the] topic/ILO be taught?' and 'before [a self-check] there
should be enough theory so the trainee can actually do that task and understand it - not 100 words of theory and the task
already.' Read by scripts/content_script.py (Stage 3 - every finding is shown on the review page and must be fixed before
approval, unless the operator approves despite it, L26) and scripts/make_architecture_page.py (Stage 2 - whether the planned
self-checks fit the module's theory time). Change a number here and both follow; nothing else restates them.

### `slide._why`
PROPOSED, awaiting Raivis's confirmation (the owner and the course office, 2026-11-25: 'less text on slides - we can put it
in the instructor notes; the presentation must be more visual with clear readable text, so the trainee can look at it and
listen to the instructor at the same time'; it replaces the 2026-09-30 decision that the theory sits on the slide). What the
trainee sees counts - the title and the lines, or on a slide of short points the title and the points. An active slide's
question, choices, whys and answer are counted on their own (beside_picture). Over target_words is a NOTE: write a plain
slide as short points ("points") - the full words stay in "text" and go to the instructor's panel, said, never cut. There is
no minimum: a short slide is fine when its picture and the instructor teach. The hard fit limits are the layout budgets
(course-module-ui knowledge/layout-templates.json "budgets").

### `points._why`
A slide of short points ("points", one a line) shows the points and keeps its "text" - the full approved words - for the
instructor's panel (data-cue). It is the shape for a plain slide over slide.target_words, with a picture or without. The
points are shorter than the text, never a copy of it.

### `notes._why`
PROPOSED, awaiting Raivis's confirmation (2026-11-25, with slide.target_words: the words leave the slide and the instructor
says them). The notes are short labelled lines, one a line: 'Say:' the full explanation the instructor gives, 'Ask:' the
question to the room, 'Show:' what to point at on the picture. They reach the instructor's panel as the slide's data-cue,
never the classroom screen. Under min_words there is too little to teach from; over max_words it is a text to read out, not a
prompt (both NOTES). Rule in force: the notes carry the full explanation as Say / Ask / Show, 20-150 words.

### `module._plain_only`
Owner, 2026-10-15 (L49, 2.26.0): counted over PLAIN theory only - the slides without "active". A slide where the trainees
predict, explain, explore or work an example fills its minutes with what they do, not with words.

### `module._why`
Across a module, the slides' own words (title and text - a slide of short points says its text to the instructor) plus the
instructor notes, divided by the slides' minutes. Under this the module's hours are claimed but not filled: the instructor
runs out of material long before the time does (must fix). The words that leave the screen are counted in the notes, so
moving them never drops a module under this: a slide of target_words and notes of max_words fill about 7.8 minutes.

### `before_self_check._cycles`
Owner, 2026-10-15 (L49, 2.26.0): short cycles - about 5 minutes of theory, then the trainees do something. It was 10 minutes
and 250 words, which pushed the class toward long plain theory. Active slides count as theory taught here: they teach. That
every answer is taught before its question (answers_taught_first) is unchanged.

### `before_self_check._why`
A self-check comes only after a block of new theory: at least this many minutes of slides and this many words (slides +
notes) since the module began or since the last task. A module whose theory is shorter than this has no self-check - its
module check covers it.

### `answer._why`
An answer the room's question opens, or the why a true-or-false opens after the vote, is the answer - two or three
sentences. Past this it is new theory hidden in a reveal, and it does not fit: it opens over the picture's column, about 120
words at 1280 x 800 and fewer on a 1024 x 768 tablet. The rest is taught on a slide before.

### `beside_picture._22px`
2026-11-25: 60 / 85 / 85 lowered in proportion to the measured beside-picture budget (85 -> 75 words) when the body text rose
to 22 px (course-module-ux measure/knowledge/floor.json "body_text") - the fit gate measures every build.

### `beside_picture._why`
What a slide with a picture beside its words holds on a 1024 x 768 tablet, measured by the fit gate on the first factory
trial's four modules. A scenario: its situation under the picture (situation), its question, choices and whys in the other
column (choices). A worked example: its steps and the room's question (steps); the answer opens over the picture. Past these
the words are cut on the tablet (must fix): trim the lines, or move a part to the slide before or to the notes (Say:).

### `answers_taught_first._why`
Every question's correct answer must be found in the slides the trainee has already seen - in what the slides show, never
only in the instructor notes - before the task opens. The check compares the correct answer's key words (numbers exactly,
words by their first five letters, so Latvian and Russian endings still match) with those slides; under this share of them,
the question asks for something not yet taught (must fix). The review page shows, for every question, the slide that teaches
its answer.

### `self_check._why`
Enough questions for the trainee's own score to mean something, few enough that the lesson keeps its pace.

### `self_check._rich`
Owner: a self-check of five is three rich tasks and two basic (match, order, choose) - at most two basic questions (the choose
and arrange families), and the rest rich up to three: a set of five 3 + 2, of three 1 + 2. Rich is a task of the locate,
operate, investigate or build family (media-and-tasks.json mechanics "family"), a scenario or a prediction (a choice with a
consequence), or any question on a 3D model, an animation or a simulator. A subject with no equipment has rich tasks too: spot
the error in a real document, check a colleague, find the fault, build the plan, fill the matrix, a scenario. Always a
must-fix: "basic_why" no longer turns it into a note (the expert reviewer, 2026-11-25: 'not the same drag-and-drop tasks every
time').

### `task_variety._why`
The expert reviewer, 2026-11-25: 'the tasks must vary much more - not the same drag-and-drop tasks every time'. Across four
built courses 84-86 % of the questions were tap an option or drag cards, though the mechanic names varied: match, sort and
order are three names and one way of answering. So variety is counted by family (media-and-tasks.json mechanics "family":
choose, decide, arrange, locate, operate, investigate, build) in every set - each self-check, the module check, the final. No
two neighbouring questions of one family; from from_questions questions on, no family takes more than max_family_share of the
set (rounded to a whole question: two of four or five, four of ten) and the set uses at least min_families families. A
must-fix in a self-check; a note in a module check or a final (content_script.py t_family_run, t_family_share,
t_few_families). The text said "must-fix in a self-check" after 2.143.1 made all three checks notes; the code is the truth:
a note everywhere.

### `team_task._why`
The expert reviewer, 2026-11-25: 'maybe group tasks instead of some self-checks' - none of four built courses had one,
though the classroom splits a class into teams (classroom-system.json team_task). One team task a module where a Sub-ILO asks
for Bloom 3 or higher: a team case, plan or drill with roles (leader, recorder, checker), in place of one self-check's Part B
- a task slide with "team": {"size", "roles", "scope"} that opens its own set (TT1, TT2 ...). Module checks and finals stay
individual. Planned at Stage 2 (make_architecture_page.py p_no_team); a note when a module of from_module_minutes or more has
none (content_script.py t_no_team).

### `module_check._why`
Every teaching module ends with one. It covers the whole module, so a short module (under before_self_check.min_minutes of
theory) still has one.

### `recap._what`
L51 (owner, 2026-10-15): every teaching module closes with ONE recap slide - "what to take away" - straight before the task
slide that opens the module check, in the same animated design in every module (course-module-ui gb_compose.css section 11,
markup in course-module-ux build/GUIDE.md). In the script it is a slide with "recap": true; its text is the points, one line
each, "Short title - one sentence". Its visual_kind is none - the design is the picture.

### `recap._why`
The owner: each module should end in the module check, but before it a beautiful summary in the same design - boxes, the main
points to take away from this module - and all modules the same closing slide design. A recap is short on purpose and is
checked by its points, not by slide.target_words; its notes are checked like every slide's.

### `split._authority`
Owner, 2026-10-15 (L49, 2.26.0): 'now most courses are 80/20 - 80 theory, 20 practical. On paper, in the programmes and IMO
model courses it stays as it is. But we want to at least come close to 20/80 - 20 plain raw theory, 80 practical:
simulators, active learning theory, self-checks, tablet interactive tasks ... first it needs to be reviewed by the person who
uses the plugin.' The programme's hours never change (L1); what changes is how the class spends them. Measured on the Stage 2
page and every Stage 3 review page. A suggestion, not a rule, in 2.26.0.

### `split._keep_theory`
Owner, 2026-10-15: 'still you need enough theory ... that does not mean you don't need raw theory at all, you can still add
it, and don't remove existing good theory, because each instructor can skip each slide faster; on paper we have that theory,
if someone needs he can read it - but the main teaching activities, how the trainee will gain this knowledge, are in active
learning.' So 20/80 is reached with TIME, never by cutting theory: every good theory slide stays (more may be added), its
minutes shrink - the instructor moves through it faster and the words stay to be read - and the minutes it frees go to active
learning. No suggestion ever says to remove a slide or cut its teaching: words that leave the screen go to the instructor
(short points, the full text to the panel; or the notes' Say:), never out of the module. The density floor still applies.

### `tablets._law`
L35 (owner, 2026-09-30). The course runs on two tablets.

### `tablets.scores` (the stamp)
Module check: ... (owner Raivis 2026-10-21, wording Aleksis 2026-10-22; replaces L45's PASSED / NOT PASSED).
