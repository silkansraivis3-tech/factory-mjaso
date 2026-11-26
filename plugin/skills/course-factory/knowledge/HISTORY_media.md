# History of media-and-tasks.json

The why, dates and owner quotes taken out of `media-and-tasks.json` so the file an agent reads holds only what a
script or a writer needs. Nothing here is read by any script. Each entry names the key it came from.

## _authority (top level)

What a slide may show besides its words, and how a trainee may answer a task - with WHO makes each one: the factory itself, the factory through the nano-banana plugin, or someone outside it. Owner, 2026-09-30 (L37, L38): 'leave place for animations, images, 3D illustrations - graphic things in slides - and mention what kind would be used', and 'make these tests more variable - not only choose A B C D - as much variable as possible ... more digitalized, more realistic, more detailed, more technical; if you cannot perform, explain why and advise how'. Read by scripts/content_script.py (Stage 3: every slide names its visual; every task names its mechanic; the variety floors are checked) and scripts/make_architecture_page.py (Stage 2: the visual plan per module and who makes it). The representations themselves - what teaches which learning need - stay with course-visuals (decide/knowledge/representations.json, learning-needs.json); each kind below names the representation it is built as.

(The file now keeps a short `_authority` with the readers and the course-visuals pointer.)

## made_by.nano_banana.how (date removed)

Said "with the owner's key (configured and working on 2026-09-30)".

## layouts.split._share, layouts.visual_wide._share, layouts.visual_full._share

- split: text 55 %, picture 45 %
- visual_wide: picture 65 %, text 35 %
- visual_full: for a 3D model, a video or an animation the instructor walks through

## mechanics._new

Owner, 2026-10-15 (L49 step 4, 2.28.0): 'tablet interactive tasks - not only drag n drop, choose e.c., something completely different, interesting and creative'. Five ways of answering added for the higher Bloom levels: find the fault (investigate), spot the errors in a filled-in document, build the plan from cards, rebuild an incident timeline, compare options side by side. How each is built on the tablet: course-task-ux section 2a.

## mechanics._law (long form)

No free typing on a self-check or module check (owner C11, course-task-ux section 2) - every mechanic below is answered by tapping, dragging or setting a control. The 'answer' format is the one line-per-item text the operator edits in the Word file; '*' marks what is right.

## mechanics._new_2_74

Owner, 2026-10-28 (2.74.0): 'more interesting / modern / technology self checks ... so self checks become practical learning as well', in two parts after each block - Part A checks everything taught before it in the module, Part B is 'a little bit difficult task, where they need to find the answer by themselves' - and '3D deck view, 3D models, equipment in 3D, panorama, on-ship activities'. Ten types, run by gb_interact.js; the approved prototypes are design/task-prototypes/index.html; the formats are scripts/interact_formats.py; how each is built: course-task-ux section 2b. 'part': 'check' is a Part A type, 'challenge' a Part B type.

## trainee_tablet_experience._law

L42 (owner, 2026-10-01): 'tablet-friendly UI/UX, user-friendly, but max modern, max technology and max understandable - so people even with zero tablet experience do the tasks, and they are excited.' The full rule: course-task-ux SKILL.md section 0.

## generation_brief._authority

Owner, 2026-10-14 (L47, 2.24.0): 'it costs approx 0.10 euro per generation, and if there is 4 developers, and they use fixes and redoings of these pictures like 10-15x, its already all billing gone ... you dont automatically connect to nano banana and do all images, you first find places where these images can be placed ... and then you ask for each place ... help me get from nano banana best result in first try by explaining in details what you want to see.'

## generation_brief.gemini_browser._authority

Owner, 2026-10-16 (via Aleksis): the AI spent its time thinking which picture to make and where - make the Gemini app in the browser (Google AI Pro, no API cost) do it, with the places and prompts already decided

## generation_brief.gemini_browser.beside_drawing._authority

Owner via Aleksis, 2026-10-16, on the tank-type, hazardous-zone and A-60 drawings: 'i need images there aswell'

## three_d._authority

Owner, 2026-10-07 (L46, 2.22.0): 'now he does 3D models almost every slide - cut it down to 50%, better not quantity but quality, use it only where it makes sense; and it lags a little in these 3D models, maybe optimisation can be considered - but mainly I love these 3D models.' Second message, same day: 'I also don't need you to cut the quality of 3D models - don't make it in all slides, about 50% of the presentation is the max that can be 3D models, but also don't cut quality, and put it only on slides where it makes sense, not only because you can.'

(Since 2.118.0 (L46) 3D has no share and no cap.)

## three_d._share

2.116.0 (operator Aleksis Vejs, 2026-11-09, after the Project Management review): the L67 share of 60-80 % 3D is REMOVED. 3D is drawn only where its why is spatial (v_why); a heavy 3D scene is a tablet-performance note (perf3d), not a share. Every 3D model is made at full quality.

## three_d._flat_words

A 3D slide whose picture description uses one of these words gets a suggestion: a 3D model of something flat adds weight, not understanding.

## three_d._fit_words

2.49.0 (operator, 2026-10-16: 'make it so they add 3D when needed'). The factory proposes a 3D model unasked: in a module with no 3D yet, the teaching slides whose title, words or planned picture name a shape, an inside or a layout in space (these words, whole-word, English) - best first, at most propose_max - are proposed as model_3d. Never a slide whose picture is a real photograph (L52 keeps it) or whose picture is flat (flat_words). The person keeps or strikes each before approving; a struck one is written in the script's "declined" and never proposed again.

## three_d._precision

2.49.2 (the IGF Module 4-15 build: 3D was proposed on procedure slides because they mention a tank, a valve, a station or a space - M09 s03, M11 s04/s08, M13 s04/s07, M14 s04/s05, M15 s02/s04 - and on an idea, M05 s05 'The barrier model - layers of protection'). A slide is proposed only when (1) the fit words are in its TITLE or its PLANNED PICTURE - at least pic_min_words different ones; words only in the slide's text do not count (a tank named in a paragraph is not a tank drawn); (2) neither the title nor the planned picture says a sequence, a document or an idea (procedure_words, besides flat_words - '3D model' in a picture description is the factory's own kind name and is not counted); (3) its picture is not planned as a flow_animation or a process_animation (not_fit_kinds - that is the author saying the lesson is a flow, which a flat animation shows better) and is not a generated (AI) picture - a scene, not a shape; (4) it is not an active slide of a kind in skip_active_lists whose text is a list of steps (a worked example). The ranking is unchanged.

## three_d._propose_first

A slide planned as a drawing of a thing (a cutaway, a section, a layout) is proposed before one planned as a step or flow animation - an animation's lesson is the sequence, and turning it into 3D can lose that. Words inside these phrases are not counted: not_fit_phrases.

## three_d.interaction (date and quote removed)

Said "(operator, 2026-10-19: 'I can't click on the elements like 01-03')".

## three_d.performance._principle

Never a lesser look to make it faster (owner, 2026-10-07: 'don't cut quality'). The speed comes from how the scenes run - one renderer, built and freed with their slide, nothing drawn or recomputed while nothing changes - not from fewer details, blurrier pictures or plainer light.

## floors._every_slide (original)

Owner, 2026-09-30 (2.18.1): no quota. As many pictures as the theory and the experience call for - wherever a picture, an animation or a realistic 3D illustration reflects what is being taught at that point, put it in; animation and 3D especially. A slide with none gets a suggestion, never a block. A picture that is named must say what it shows (must fix), and an unknown kind is a mistake to correct. 3D is the exception (owner, 2026-10-07, L46): at most half of a module's pictures, and only where it makes sense - see three_d.

(Wrong since 2.118.0: 3D has no share and no cap. The live note was corrected.)

## floors._moving

A suggestion, not a rule (2.18.1): a module with this many minutes of theory and nothing that moves, turns or can be explored is pointed out, because where something moves, changes state or has an inside, a still picture teaches it worse (course-visuals, learning-needs.json).

## floors._ai_scene

2.49.0 (operator, 2026-10-16: 'add AI generated photos when needed'). Where no real photograph exists, a realistic AI picture can set the scene - never equipment a trainee must recognise (L33), never instead of a photo that can be taken (L52). The factory proposes it unasked: in a module with no AI picture yet, a teaching slide with no picture, or whose planned picture is a schematic or none and whose words name a scene or a situation (these words) - at most ai_propose_max - is proposed as ai_illustration. Planning it costs nothing; each picture is still described, priced and said yes to before it is made (nano-banana, L47). A struck one goes in the script's "declined".

## floors._real_photos

L52 (owner, 2026-10-15: 'add as many real photos as possible'). A teaching slide counts when its picture is a real photograph, a real film or a 3D scan - or its planned picture says a real photograph goes beside the drawing (the build sheet's inset). Fewer than half is pointed out as a suggestion: wherever a camera can show it, a real photograph goes in - as the slide's picture or beside the drawing. Never an AI picture of equipment a trainee must recognise (L33).

## floors._photo_things

L57 (operator, 2026-10-15). A part a drawing names counts as a real thing - one a camera can show - when its last word is one of these (plural or not), or when a photo's 'shows' names it. Each such part on a drawn slide gets its real photograph beside the drawing, matched by the photo's 'shows' in _photo_meta.json; a part with no photo is reported at build and goes on working_claude\PHOTOS_TO_TAKE.md.

## floors._kinds

A suggestion, not a rule (2.18.1): a module of 6 slides or more with fewer than 3 kinds of picture is pointed out - but a picture is never added only for variety (L13).

## floors._tasks

A self-check uses at least 2 different mechanics and a module check at least 3; 'choose one answer' is at most 40 % of a module's questions; every module has at least one hands-on question - locate, operate or decide on something that looks like the real thing; never more than 2 questions of the same mechanic in a row. These stay rules (owner, 2026-09-30). The final assessment follows the programme's own format - none of them applies to it.
