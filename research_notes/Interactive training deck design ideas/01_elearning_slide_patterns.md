# E-learning and interactive presentation slide patterns (catalogue for NOVIKONTAS one-page decks)

Method note: Articulate community pages (community.articulate.com) returned HTTP 403 to fetch, Elucidat's showcase redirected away, and no Brandon Hall/Learning Technologies winning-course detail was retrievable (awards are announced per vendor, not per course design). Coverage of award winners is therefore thin; the catalogue is built from vendor docs and recap titles that could be read. Items marked "Cheap" are judged by me for plain HTML/SVG/JS.

## 1. What block/slide types recur in authoring-tool ecosystems (Rise 360, Storyline, Genially, Elucidat)

### Takeaway
Rise 360's block taxonomy is the best-documented "vocabulary" of recurring e-learning screen types: about a dozen interactive blocks plus statement/quote/gallery/knowledge-check blocks. Community challenge recaps (385+ challenges) confirm the same handful of patterns recur: tabs, accordion/click-to-reveal, labeled graphic/hotspot, before-after comparison, slider, timeline/process, flashcards, branching scenario, sorting/matching.

### Cited Findings
- Rise 360 interactive blocks: Accordion, Tabs, Labeled graphic (image with clickable labels), Process (step-by-step stages), Scenario (branching decisions), Sorting activity (order or categorise), Timeline, Flashcard grid, Flashcard stack, Button, Button stack, Storyline embed — [Articulate: Rise 360 Lesson and Block Types](https://www.articulatesupport.com/de/article/Rise-Lesson-and-Block-Types)
- Rise 360 non-interactive blocks worth copying as layouts: Statement A-D (key-info callouts), Note, Quote on image, Quote carousel, Checkbox list, Text on image, Banner, Image full width, Carousel and 2/3/4-column grids, Table, Continue divider (gate: learner must click before content continues), Numbered divider (section number) — [same source](https://www.articulatesupport.com/de/article/Rise-Lesson-and-Block-Types)
- Rise knowledge-check blocks: multiple choice, multiple select, fill in the blank, matching, question bank (random draw) — [same source](https://www.articulatesupport.com/de/article/Rise-Lesson-and-Block-Types)
- Rise also has Code blocks and Custom blocks for hand-built HTML/CSS/JS interactions (AI-licence only); Storyline blocks cannot be nested inside tabs/accordion/process — [Rise block search summary](https://access.articulate.com/support/article/Rise-Lesson-and-Block-Types)
- Articulate Community's weekly challenges have produced recap pages per pattern (counts: 385 challenges, ~10,972 examples by one post). Pattern-named recaps found: Tabs interactions (#448), Before/After comparisons (#335, #100), image sliders and photo galleries (#84), interactive documents with sliders (#300), interactive sliders (#205), gate screens (#3), lightbox slides, virtual tours, interactive magazines, branching scenarios, quiz makeovers/results slides (#14), badges and awards (#197), call-centre scenarios (#47) — e.g. [Before/After #335](https://community.articulate.com/articles/showing-before-and-after-comparisons-in-e-learning-335), [Image sliders #84](https://community.articulate.com/articles/using-image-sliders-and-photo-galleries-in-online-courses-84), [Sliders #300](https://community.articulate.com/articles/creating-interactive-documents-with-sliders-in-e-learning-300), [Tabs #448](https://community.articulate.com/blog/e-learning-challenges/using-tabs-interactions-in-e-learning-448/1110629), [Gate screens #3](https://community.articulate.com/articles/e-learning-challenge-3-gate-screens-in-online-courses), [Virtual tours](https://community.articulate.com/articles/virtual-tours-elearning), [Interactive comparisons](https://community.articulate.com/articles/interactive-comparisons-in-elearning), [Series index](https://community.articulate.com/category/e-learning-challenges-and-recaps) (all fetch-blocked; titles/summaries only from search)
- Genially: content types presentation, interactive image (clickable hotspots opening text, links, extra photos), infographic, gamification (hidden picture, flashcards, quiz games), digital escape room/breakout — [Genially directory entry](https://elearningindustry.com/directory/elearning-software/genially), [teacher guide](https://ditchthattextbook.com/gamified-genially/)
- Adobe's 2026 guide lists six recurring patterns: drag-and-drop matching, scenario questions with instant feedback, branching scenarios with consequences, interactive-video hotspots, simulated software/virtual labs, role-play; and the rule "tie every interaction to an objective, cut busywork interactions", checks after each key section — [Adobe eLearning, Jan 2026](https://elearning.adobe.com/2026/01/how-to-design-interactive-e-learning-experiences-that-truly-engage-modern-learners/)
- Brandon Hall 2025 technology awards were won by vendors for e.g. simulation/gaming (Scheer IMC, AI dialogue training), video with AI avatars (ValGenesis); no slide-level design detail published — [Scheer IMC](https://www.scheer-imc.com/newsroom/news/scheer-imc-wins-two-brandon-hall-group-excellence-in-technology-awards/), [ValGenesis](https://www.businesswire.com/news/home/20250114621172/en/ValGenesis-Wins-Gold-in-Brandon-Hall-Group%E2%80%99s-Excellence-in-Technology-Awards)
- SmartBuilder's example gallery includes technical simulations: slider simulation (light wavelength vs solar power), parameter-twiddling equipment simulation (weather/time/direction vs panel output), hardware connection simulation (drag cables), software task simulation with performance meters/hints/counters, multi-step chemical spill handling — [SmartBuilder examples](https://www.smartbuilder.com/elearning-examples/)

### Inferences
- The vocabulary to cover is small: **reveal (accordion/tabs/click-to-reveal), labeled image (hotspot), before/after, slider, process/timeline, flashcard, sort/match, scenario, gate/continue, key-takeaway statement**. Each is a few lines of HTML/SVG/JS. Cheap: all of them. Medium: branching scenario state machine, drag-sort with touch.
- Gate ("Continue") divider maps directly to our Next-step runner: content below does not appear until the instructor/trainee confirms.
- "Statement" callout variants (A-D) suggest a small fixed set of takeaway styles rather than ad-hoc boxes.
- Quiz-results/badge recaps are gamification patterns of questionable value for accredited training; treat as optional.

### Gaps
- No award-winning course walkthroughs (Brandon Hall, Learning Technologies, eLearning Industry) with slide-level detail could be retrieved; Elucidat showcase and Adobe Captivate showcases not reachable. Articulate community example URLs could not be opened to verify quality.

## 2. HTML presentation frameworks: what builds look professional vs gimmicky

### Takeaway
reveal.js and Slidev give three professional build primitives: fragments/clicks (progressive disclosure), auto-animate/magic-move (state morph between two adjacent states of the same objects), and stacked swap (r-stack). Their value comes from preserving object identity across steps, not from flashy transitions.

### Cited Findings
- reveal.js auto-animate morphs elements between two adjacent slides marked `data-auto-animate`; matches by identical text/node type, image/video/iframe `src`, or forced with `data-id`; list items match individually; code blocks animate with `data-line-numbers` and matching `data-id`; default ease 1.0 s (`data-auto-animate-duration`, `-easing`, per-element delay); unmatched elements fade in by default or appear instantly if set false — [reveal.js Auto-Animate](https://revealjs.com/auto-animate/)
- reveal.js fragments: entrance (fade-in, fade-up/down/left/right, grow), exit (fade-out, semi-fade-out, shrink, strike), combined (fade-in-then-out, current-visible, fade-in-then-semi-out), colour highlights (highlight-red/green/blue; highlight-current-* revert on next step); order by DOM or `data-fragment-index` (several elements can share an index); nesting wrappers chains effects across steps — [reveal.js Fragments](https://revealjs.com/fragments/)
- `r-stack` (reveal.js 4.1+) layers children centred on top of each other so each fragment replaces the previous; known issue: table rows duplicate instead of swapping — [reveal.js issue 745 thread](https://github.com/hakimel/reveal.js/issues/745)
- Slidev: click = animation unit; `v-click`, `v-after` (with previous), `v-clicks` (every list item, `depth`, `every`), `at` for relative/absolute timing, `v-switch`, `clicks` override, presets fade/up/scale; `v-motion` enter/leave variants per click; slide transitions fade, slide-left/right/up/down, view-transition (experimental), different transition for forward vs backward navigation — [Slidev animations](https://sli.dev/guide/animations)
- Slidev Magic Move (v0.48.0, March 2024) morphs code between steps bound to clicks, default 800 ms — [Slidev Shiki Magic Move](https://sli.dev/features/shiki-magic-move)
- Slidev presenter mode shows notes, timer, click counter, remote control — [Slidev releases](https://github.com/slidevjs/slidev/releases/tag/v0.48.0)
- Pitch allows interactive embeds (videos, booking) inside decks — [Mentimeter blog comparison](https://www.mentimeter.com/blog/business/slido-alternatives). No sourced material found on Gamma, Prezi, Spectacle or Apple Keynote design.

### Inferences (design judgement, not sourced)
- Professional: same object persists and moves (pipe highlights, valve changes state, camera tilts) so the viewer tracks cause and effect; one easing curve and ~0.4-0.8 s everywhere; fade/up fragments; highlight-current to point at one step while dimming others (semi-fade-out).
- Gimmicky: per-slide different transitions, spin/zoom between unrelated slides, long Prezi-style zoom for decoration, bullets flying in one by one.
- For our deck: a "scene stays, annotation steps change" structure (Cheap: CSS class toggles on SVG groups per Next press; r-stack-like absolutely positioned layers). Auto-animate-style FLIP morph between two layouts is Medium (Web Animations API or View Transitions API).

### Gaps
- Not covered: Gamma, Prezi, Spectacle, Keynote specifics, reveal.js showcase decks (no sourced pages retrieved).

## 3. Instructor-led interactive features (polls, hotspots, sliders, scenarios)

### Takeaway
Classroom tools converge on a short list of response types, and the instructor-pacing controls (lock/unlock screens, timers, teacher-paced vs student-paced) matter as much as the question types. Pin-on-image and drag/draw are the closest to hotspot-style trainee answers and are only partly available in these tools.

### Cited Findings
- Mentimeter (12 types free/13 Pro): multiple choice, open ended, ranking, guess the number, word cloud, scales, Q&A, 100 points, 2x2 grid, pin on image, quiz, quick form; mostly synchronous, survey mode for self-paced, no locks/timers — [FLT Mag comparison, July 2024](https://fltmag.com/interactive-slides-comparison/)
- Pear Deck: text, choice, number, website; draw and draggable (paid); teacher-paced with optional student-paced mode — [FLT Mag](https://fltmag.com/interactive-slides-comparison/)
- Nearpod: open-ended, poll, collaborate board, quiz, draw it, fill in the blanks, memory test, matching pairs, time to climb (game quiz), drag & drop (paid); teacher can lock/unlock screens, add timers; also 3D object, simulation, VR field trip content types — [FLT Mag](https://fltmag.com/interactive-slides-comparison/), [Nearpod guide PDF](https://www.yonkerspublicschools.org//cms/lib/NY01814060/Centricity/Domain/8217/Nearpod%20Quick%20Guide1.pdf)
- Curipod: open question, drawings, poll, word cloud; instructor can freeze a slide and add or subtract 30 s — [FLT Mag](https://fltmag.com/interactive-slides-comparison/)
- Mentimeter's word cloud/instant feedback rated more engaging than Pear Deck in G2 reviews (reviewer opinion) — [G2](https://www.g2.com/compare/mentimeter-vs-pear-deck)
- Hotspot pattern: transparent clickable areas over a high-res photo (e.g. medical device, factory floor) revealing hidden information; branching built from choice hotspots triggering the next slide — [CommLab India](https://www.commlabindia.com/blog/interactive-elearning-design), [Tara Bryan branching](https://taralbryan.com/branching-scenarios-in-e-learning-challenge/)
- Before/after: Articulate recaps cite sliders, toggle buttons/switches, and video; example of a slider showing bears before/after hibernation — [Articulate #335/#100](https://community.articulate.com/articles/before-after-elearning)
- Elucidat showcase highlights learners seeing consequences of right/wrong branching choices — [Arlo/Elucidat summary via search](https://www.elucidat.com/showcase/)

### Inferences
- Our model (instructor projects, tablets answer) matches Nearpod/Pear Deck teacher-paced mode: instructor presses Next = "unlock screen"; add a timer and lock. Aggregate result reveal (bar per option, pin-on-image heat dots from all tablets) is the strongest copyable pattern. Needs a tablet-to-projector channel (WebSocket/BroadcastChannel); Medium.
- Cheap in plain HTML/SVG/JS: hotspot reveal (SVG hit areas on a photo), before/after slider (clip-path + range input), zoom-into-photo callout (CSS transform on a viewBox/crop with a lens ring), progressive-disclosure callouts, slider-driven simulation (range input mapped to SVG parameters), flashcards (CSS 3D flip), two-column compare toggle.
- Branching scenario: Medium (state object + outcome screens); highest value when consequence is shown on the equipment (valve position, gas reading) not just text.

### Gaps
- Kahoot and Slido specifics were not retrieved; ClassPoint not searched. No source found on tablet-to-projector response reveal architecture.

## 4. Patterns suited to technical/industrial procedure teaching

### Takeaway
Sources for industrial/oil-and-gas training show one repeated structure: pre-test, guided step-by-step simulation, monitored interaction, knowledge check/certification. Equipment simulations where the learner manipulates parameters or connects components are the typical interactive centrepiece.

### Cited Findings
- A patent-described training flow: pre-test, instruction, interactive simulation, monitoring, knowledge test, positioned as better than linear video — [USPTO 5590057](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/5590057)
- E-Spaces 3D simulators list step-by-step demonstration of start-up, maintenance and procedures — [E-Spaces brochure](https://e-spaces.com/cortona/Brochure.pdf)
- Rheinmetall process rig trainer: start-up/shut-down procedures with pass/fail questionnaire per e-learning module — [Rheinmetall PDF](https://www.rheinmetall.com/Rheinmetall%20Group/Systeme%20und%20Produkte/Simulation%20%26%20Ausbildung/Ausbildung%20Energie/Rheinmetall-Zivile-Ausbildungsloesungen-Energie-CAPP-OilGas-TC.pdf)
- INPEX Ichthys LNG project used custom online 3D models of onshore/offshore facilities for training — [Offshore Technology](https://www.offshore-technology.com/features/featurevirtual-realities-simulation-tech-for-offshore-safety-4198094/)
- SmartBuilder technical examples (slider simulation, parameter simulation, hardware connection, performance meters/hints/counters, multi-step chemical spill) — [SmartBuilder](https://www.smartbuilder.com/elearning-examples/)
- Adobe: base scenarios on workplace tasks; formative checks after each section; simulated environments/virtual labs — [Adobe 2026](https://elearning.adobe.com/2026/01/how-to-design-interactive-e-learning-experiences-that-truly-engage-modern-learners/)

### Inferences (my proposals for gas carrier / IGF material)
Cheap-to-build candidates:
1. **Numbered procedure stepper**: P&ID/photo stays, Next highlights next valve/step, previous steps dim (semi-fade-out), live state labels (open/closed, pressure). Cheap.
2. **Valve/state toggle simulator**: learner or instructor taps valves; downstream pipes recolour; wrong order triggers consequence screen. Cheap-Medium (state graph).
3. **Parameter slider**: temperature/pressure vs phase, boil-off, tank filling level; mapped to SVG. Cheap.
4. **Photo hotspot "find the item/identify the hazard"** with tablet pin-on-image and instructor heat-map. Cheap + shared channel Medium.
5. **Before/after or normal/abnormal compare**: correct vs faulty alarm panel, frosted vs normal pipe. Cheap.
6. **Sequence ordering (drag-sort)** for startup/emergency shutdown steps with explanation on wrong order. Medium on touch.
7. **Consequence branching scenario** (leak detection decision tree) with equipment state shown. Medium.
8. **Cutaway/zoom-into-photo callout**: tap region, lens zoom with label. Cheap.
9. **Gate screen / confirm checkpoint** before next phase, instructor-controlled, mirroring real "permission to proceed" culture. Cheap.
10. **Pre-test poll then post-check poll** with aggregate reveal. Medium.

### Gaps
- No peer-reviewed or award-judge source stating which patterns are best for procedural teaching; the list above is inference. No LNG/gas-specific e-learning design sources found beyond the INPEX 3D mention.
