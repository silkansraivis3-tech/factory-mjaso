# History of the numbers in the layout templates

Why a number in `layout-templates.json` is what it is, moved out of the JSON so the file agents read holds rules and
values only. Nothing here is read by a script. Each entry names the key path it came from.

## layout-templates.json

### `_authority`
Owner, 2026-10-20 (L61, course-factory 2.52.0): 'implement the layout templates. All slides for all modules that will be made
need to be in this style, it's a RULE. Configure the compiler so it does this style - of course the logo should be our
official one, and the colours from the brandbook.' The design is the owner-reviewed library design/course-layout-templates/
(preview.html, 13 templates, 2026-10-20); this file is its production contract.

### `split._why`
2.116.0 (operator Aleksis Vejs, 2026-11-09): the figure gets the share it needs - 40 % of the slide up to the whole slide;
the old 50-60 % text band is no constraint. Default 55 / 45. A build sheet may set "split": 0.2 ... 0.6 (the text share).

### `boxes._why`
The picture's box on a slide with words beside a picture comes in four sizes. The compiler (compile/scripts/layout_fit.py)
gives a picture the smallest box that shows it readably and holds the words beside it; when the words do not fit beside that
box they go in parts, and when a picture needs more than any box beside words (or growing it would cost the words more than
extra_parts more parts) the factory does not squeeze it - the picture goes on the slide alone (figure-stage) or is made
another kind of picture. A build sheet may name a box ("box": "picture-wide").

### `boxes._words`
even is the measured beside_picture budget; the others in proportion to their column (at 22 px body text: 93 / 85 / 65 / 54
-> 82 / 75 / 57 / 48) - starting values, the audits and the fit gate measure every build.

### `boxes._three_d`
2.69.0: a 3D model beside words always has at least picture-wide (at 40-50 % the models were almost invisible).

### `variety._why`
Owner, 2026-10-21 (L62): 'make sure that two types of slides never repeat in a row - now 6-7 slides are exactly the same
layout, and it hurts the eyes'. A slide's look is its template, its variant and its ground (light, or dark / photo). Two
slides next to each other never look the same: when a slide would repeat the one before it, the compiler builds it another
way that holds its words and picture - the picture on the other side, the other ground, a photograph framed on the dark
ground, a drawing on the stage - and it avoids the look of the slide before that one too.

### `variety._measured`
2.63.0: framed photo 100 -> 50 and picture-top 110 -> 70 words, from the measured budgets in "budgets" (IGF M04 s05: 102
words under a photograph across the slide spilled 66 px). 2026-11-25, body text 22 px: picture-top 70 -> 45 (measured), stage
45 -> 40 (in proportion, not measured).

### `variety._shape` (the stale part)
The text said a photograph across the slide held "up to 110 words" next to picture_top_max_words 45 and
budgets.under_top_photo 45; the number in the text was the pre-22 px one and is now 45.

### `dense._why`
2.116.0: a NOTE only - 'dense' is more than 60 words on the slide. A dense slide may have no picture when its words read on
their own; there is no picture quota. The compiler never cuts or moves words by itself: the writer moves them, as a slide of
short points whose full words go to the instructor (course-factory theory-rules.json "slide", "points").

### `parts._why`
2.116.0 (operator, 2026-11-09): the factory NEVER pages the words by itself. auto_from_words is only the writer's threshold
(v_paged_slide: more words than a picture's column holds - the writer makes them short points, the full words to the
instructor, with the operator's approval); content-in-parts is built only when a build sheet asks for it ("template":
"content-in-parts" / "parts"), then its lines in order, in parts of about part_words words, Next walks the parts. 2.63.0: 135
/ 110 were starting values; measured (see budgets) the column beside a picture holds 85 words at 1024 x 768 and a part 75 -
90-135 words beside a picture spilled 19-91 px, a part of 85 spilled 68 px. 2026-11-25, body text 22 px: 75 / 65 (measured,
see budgets).

### `budgets._why`
2.63.0 - how many words fit, MEASURED with the real compiler, these templates and the larger logo: four texts of every length
cut from the IGF Basic scripts' own lines (a statement and bullets), each slide alone between short text slides, judged by
run_audits.py (the build's gate) at 1024 x 768 - the binding size - and 1280 x 800. A budget is the longest length at which
all four fitted. The compiler's layout choice uses them (the thresholds above and below are set from them), and a slide built
over its layout's budget gets an early warning at compile.

### `budgets.measured`
2026-10-21, course-factory 2.63.0; again 2026-11-25 with the 22 px body text (course-module-ux measure/knowledge/floor.json
"body_text"; measure_word_budgets.py on the IGF Basic scripts again) - every budget but the framed photo went down.

### `budgets._first_spill`
Beside a picture 90 words (2 of 4 texts, 19 px), with a photo under the words 75 (1/4, 10 px), photo column 90 (2/4), under a
top photo 75 (3/4, 71 px; one 55-word text spilled 31 px), on a full-screen photo 55 (1/4), framed photo 60 (2/4, 40 px), two
parts of 85 words (3/4, 68 px). At 22 px: beside a picture 80, with a photo under the words 60, photo column 80, under a top
photo 50, full-screen photo 50, framed photo 55, a part of 75 (35-37 px); parts of 65 and less leave one 11-12 px spill in two
of eight texts, the same at 60 and 55 - not the part's size.

### `mix._why`
2.127.0 (operator Aleksis Vejs, 2026-11-10: 'the factory doesn't really want to use the template'). Counted on the built
decks: Project Management 42 of 57 teaching slides plain (a picture beside ordinary lines), the safety course 150 of 150; ten
of the twenty-one templates in no deck at all. The picking table was an invitation only - nothing said when a slide's own
words already had the shape of a template. Now the script check (content_script.template_findings) reads every PLAIN teaching
slide - no field or line shape of a template, no template asked for in the build sheet - and names the template its words fit
and how to write them (t_fits_template, a suggestion). The module is a MUST-FIX (t_template_mix) only when more than
max_plain_share of its teaching slides are plain AND the check can name slides that fit a template: there is always something
concrete to do, and no rule to satisfy by guessing. The operator who wants the module plain says why ("plain_why" at the top
of the script): then a note.

### `mix._values`
Starting values - 0.6: the two courses counted above are over it, a module with four plain slides in ten is not. min_slides: a
module too short to judge is left alone.

### `picking._why`
The templates hold no words of their own; the factory picks the right one for each piece of a new course's information. It
reads what each piece of the module's information is and writes the script so (content script fields) and the build sheet so
(pictures); the compiler then builds the template. Read by the script guide (script/GUIDE.md section 5c) and the compiler
(shaped_template, auto_template). Always: never the same look twice in a row (L62), 60-80 % of the slides with interactive 3D,
no flat drawings (L67).
