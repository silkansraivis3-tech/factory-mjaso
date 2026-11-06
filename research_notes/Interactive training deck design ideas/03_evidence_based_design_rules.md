# Evidence-based design rules for projected training decks (1920x1080) and tablet tasks

Method note: search snippets were mostly secondary; several primary pages (ScienceDirect, Material, assertion-evidence.com) returned 403/404 or no numbers. Where a number is not from a source it is in Inferences and labelled "factory proposal". Tablet/projector specifics are largely engineering convention, not studied effects.

## 1. Learning science: Mayer, Sweller, animation vs static

### Takeaway
Mayer's reducing-extraneous-load principles (coherence, redundancy, spatial contiguity, signaling) have medium-to-large median effects; segmenting, pre-training and modality ~d 0.75-0.8. Animation beats static graphics only modestly overall (d 0.37 -> g 0.23), but strongly when the learner must learn the specifics of a change (flow, motion, sequence).

### Cited Findings
- Median effect sizes (2014 Cambridge Handbook chapter): coherence 0.86 (23/23 tests), signaling 0.41 (24/28), redundancy 0.86 (16/16). Later review figures differ: coherence 0.70, signaling 0.46, redundancy 0.87, spatial contiguity 0.79. Sources disagree, cite as ranges, "medium to large" — [Cambridge Handbook ch.](https://resolve-he.cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/principles-for-reducing-extraneous-processing-in-multimedia-learning-coherence-signaling-redundancy-spatial-contiguity-and-temporal-contiguity-principles/CD5B7AE1279A9AB81F8EEBB53DBEC86E); [JCAL summary via search](https://link.springer.com/10.1007/s10639-022-11283-2)
- Segmenting median d 0.79 (10/10 tests), pre-training 0.75 (13/16), modality 0.76 (61 tests) — [Cambridge Handbook ch.](https://cambridge.org/core/books/cambridge-handbook-of-multimedia-learning/principles-for-managing-essential-processing-in-multimedia-learning-segmenting-pretraining-and-modality-principles/DD24C2F48B9B1277CE59F78276110258)
- Meta-analysis of 181 Mayer-corpus studies (1990-2022): overall Hedges g 0.37; personalization and modality among the largest; some principles stronger for low-prior-knowledge learners (boundary condition) — [search summary](https://par.nsf.gov/biblio/10637927); [Cambridge](https://www.cambridge.org/core/books/abs/multimedia-learning/science-of-instruction-determining-what-works-in-multimedia-learning/42AFD700BB12A65BA6DCDDA833326B33)
- Not found: 3rd-edition medians for personalization and embodiment.
- Sweller CLT: worked-example effect (novices learn more from studied solutions than unaided problem solving); expertise reversal (benefit fades, eventually redundant, as expertise grows); split-attention (separated sources raise extraneous load; integrate text into the diagram, Chandler & Sweller 1992) — [Teacher Magazine](https://www.teachermagazine.com/au_en/articles/cognitive-load-theory-teaching-strategies); [Expertise reversal](https://en.wikipedia.org/wiki/Expertise_reversal_effect)
- Animation vs static: Höffler & Leutner 2007, d = 0.37 (95% CI 0.25-0.49; 26 studies, 76 comparisons) — [Leibniz IPN](https://www.leibniz-ipn.de/en/research/publications/instructional-animation-versus-static-pictures-a-meta-analysis). Berney & Bétrancourt 2016 g = 0.226 (CI 0.12-0.33; reported as 140 comparisons/61 studies by one source, 76/26 by another: unresolved), Castro-Alonso 2019 g = 0.23 — [Springer 2021](https://link.springer.com/article/10.1007/s11251-021-09541-w)
- Re-analysis (Plötzner, Berney, Bétrancourt): animation is considerably better when the specifics of change must be learned — [Springer 2021](https://link.springer.com/article/10.1007/s11251-021-09541-w)
- Mayer-aligned instructional animation guide (practitioner): [eLearning Coach](https://theelearningcoach.com/learning/animation-and-learning/) (not read in detail).

### Inferences
- Factory proposals: no decoration (coherence); label on or touching the part, never a legend (spatial contiguity); short caption for the instructor to narrate, not read aloud (redundancy: do not duplicate spoken text on screen); highlight (signal) the part being discussed, dim the rest; one build step = one segment; pre-train key terms/components before the process animation; novices get worked examples first then faded, advanced trainees get fewer scaffolds (expertise reversal).
- Animate only a change the trainee must learn (flow direction, valve state sequence, pressure rise); for static structure use a still image. Expected benefit is small otherwise.
- Pace: animation must be segmented and pausable/step-controlled (presenter Next press) to limit transient information; this is Mayer-consistent but specific moderators were not verified here.

### Gaps
- Primary-text moderator results (procedural-motor, realism, signaling in animation) not retrieved (403/PDF unreadable).
- Embodiment/personalization medians; whether effects hold for projected classroom with instructor narration (most studies are individual screen learning).

## 2. Slide design frameworks and density

### Takeaway
Sentence-headline + visual evidence (assertion-evidence) gives better delayed comprehension and fewer misconceptions than topic-bullet slides; the evidence is real but modest and partly non-significant. Duarte's 3-second glance test and Tufte's bullet critique both argue for one idea per screen.

### Cited Findings
- Assertion-evidence: 111 students (55 topic-subtopic vs 56 A-E) heard the same lecture; A-E scored higher on complex-concept comprehension (ASEE 2011) — [ASEE](https://peer.asee.org/17510)
- Garner & Alley 2013, 110 engineering students: better comprehension, fewer misconceptions, lower perceived cognitive load, better recall at one-week delayed test — [IJEE 29(6)](https://www.ijee.ie/articles/Vol29-6/23_ijee2791ns.pdf)
- Common-practice slides helped short-term recall of simple statistics, A-E helped long-term recall of key ideas; a follow-up found the A-E trend not statistically significant and suggested the quality of the visual evidence matters most — [Penn State](https://pure.psu.edu/en/publications/high-quality-visual-evidence-on-presentation-slides-may-offset-th-2/); [WUSTL CTL](https://ctl.wustl.edu/in-powerpoint-its-the-headline-that-makes-the-difference/)
- Alley's site: succinct sentence assertion headline, visual evidence instead of bullet lists; no numeric limits on that page — [assertion-evidence.com](https://www.assertion-evidence.com/)
- Duarte glance test: the main point understood in 3 seconds or less; "one idea per slide" — [Duarte](https://www.duarte.com/resources/slide-glance-test/). Critique: dense strategy/ops slides will not pass; not every slide must — same search.
- Tufte: bullets are "faux analytical", convey only sequence, priority, set membership; slides' low resolution means ~40 words, about 8 seconds of reading (secondary summary) — [Tufte pamphlet notes](https://www.inf.ed.ac.uk/teaching/courses/pi/2016_2017/phil/tufte-powerpoint.pdf); rebuttal [Atkinson](https://www.robertgaskins.com/files/five-experts-dispute-edward-tufte-on-powerpoint-sociable-media-cliff-atkinson.htm)

### Inferences
- Factory proposal: headline = one full sentence claim (about 8-14 words, max 2 lines); body = one figure/photo/diagram; at most ~25-30 words of on-screen text beyond labels; at most 3-4 new elements per build step (working-memory convention, not sourced here). A glance-test audit: single focal point, 3-second takeaway.
- Procedures (ordered steps) are the legitimate exception to "no list": render as numbered sequence builds, one step per Next, with step highlighted (signaling + segmenting).
- Presenter-led recall of numbers (set-points, limits) may need a short written value; A-E hurts short-term recall of bare statistics, so put key numbers in the figure label.

### Gaps
- Primary Duarte numerics (words per slide) and Tufte data-ink-on-slides not found. Reynolds/Presentation Zen not searched.

## 3. Projected legibility, contrast, colour, safety colours

### Takeaway
Size for the last row: min text height about 1/50 of screen height (about 22 px at 1080 for the very minimum), body well above that. Light-on-dark vs dark-on-light is not settled for projection; choose by room light and verify contrast, not by trend.

### Cited Findings
- 8H rule: furthest viewer no more than 8x screen height; minimum legible text height about 1/50 of screen height; double it if the room is twice as long; it is a minimum not an ideal; origin is an AV rule of thumb with no primary study found — [PPT FAQ](https://www.pptfaq.com/FAQ00125_How_big_should_text_be-_What-s_the_ideal_font_size-.htm); [ProAV](https://www.proav.de/video/projectionrules.html)
- Stricter variants: 1/25 of screen height for small projectors; university guide: body 24-32 pt, 20 pt absolute minimum — [PPT FAQ](https://www.pptfaq.com/FAQ00125_How_big_should_text_be-_What-s_the_ideal_font_size-.htm); [UW-Parkside](https://www.uwp.edu/explore/offices/campustechnologyservices/innovationsinlearning/upload/2010-08-13_Slide_Present_Tips_ETTE.pdf)
- WCAG 2.2: text contrast 4.5:1 (AA), 3:1 for large text (>=18pt/24px regular or 14pt/18.66px bold), 7:1 / 4.5:1 AAA; non-text (icons, borders, state) 3:1 — [WebAIM](https://webaim.org/articles/contrast/); [Stark](https://www.getstark.co/wcag-explained/perceivable/distinguishable/contrast-minimum/)
- Polarity: positive polarity (dark on light) is better for normal vision, mostly due to luminance; no daytime effect, light mode better at night in Dobres et al.; nothing found on projectors; NN/g has no own dark-mode research — [NN/g](https://www.nngroup.com/articles/dark-mode/); [Düsseldorf](https://docserv.uni-duesseldorf.de/servlets/DerivateServlet/Derivate-31413)
- Line length 45-90 characters (including spaces); line spacing 120-145% of size; web body 15-25 px — [Butterick](https://practicaltypography.com/summary-of-key-rules.html); [line length](https://practicaltypography.com/line-length.html)
- Okabe-Ito colour-blind-safe palette: #E69F00, #56B4E9, #009E73, #F0E442, #0072B2, #D55E00, #CC79A7, #000000; roughly 8% of men have a colour-vision deficiency (not primary-checked) — [NYU Siegal](https://siegal.bio.nyu.edu/color-palette/)
- ISO 3864: red/white = prohibition, fire equipment; yellow/black = hazard; blue/white = mandatory; green/white = safe condition. ANSI Z535: DANGER red, WARNING orange, CAUTION yellow, NOTICE blue, SAFETY green. Hex values vary by edition; check ISO 3864-4 / Z535.1 — [Wikipedia ISO 3864](https://en.wikipedia.org/wiki/ISO_3864); [InCompliance](https://incompliancemag.com/ansi-z535-1-safety-colors-in-focus/)

### Inferences
- Unit conversion (my arithmetic): 1080 px tall slide; PowerPoint 16:9 is 540 pt tall, so 1 pt = 2 px. The 20 pt minimum is 40 px; 24-32 pt body is 48-64 px. 1/50 of 1080 = 22 px, but that counts text height, not font-size (cap/x-height smaller than the em), so do not read it as the font px. Factory proposal: body >=40 px (hard floor 32 px for captions/labels, flagged), headings 64-96 px; 1/25 rule gives 43 px for a long room.
- Projector washout: factory proposal to design for contrast >=7:1 on main text and >=4.5:1 on secondary, since projected black level is raised by ambient light (no source; verify on the classroom projector).
- Do not rely on colour alone for hazard/valve state (add icon/shape/label); keep ISO red/yellow/green only for their safety meaning; use the Okabe-Ito set for categorical data, avoiding red-green pairs.
- Light slides in a lit classroom, dark in a dimmed room with photos; the deck already has two modes, so choose per room lighting (no projector-specific study found).

### Gaps
- No primary study on font size vs. distance (only AV rule of thumb); no projector-specific polarity data; no word-count research behind Tufte's "40 words".

## 4. Visual craft, motion and avoiding template look

### Takeaway
Use a small hand-picked type scale, consistent spacing grid, high contrast hierarchy and deliberate whitespace; motion durations in the 200-400 ms range with decelerate easing for entrances, only to explain change. Specific design-craft numbers here are mostly practitioner convention.

### Cited Findings
- Refactoring UI (via secondary summaries): hand-picked type scale 12/14/16/18/20/24/30/36/48/60/72 px; smaller text gets more line height (1.5-1.75 for 14 px), headlines 1.0-1.1; 45-75 characters per line; limit shadows to show elevation; do not use grey text on colour, tint from the background hue instead; white at reduced opacity looks washed out — [skills.cat summary](https://skills.cat/skills/futuregerald/futuregerald-claude-plugin/ui-design); [ui-skills](https://www.ui-skills.com/skills/s0xdk/refactoring-ui) (secondary, book not read; summaries conflict on 1.25 modular vs hand-picked)
- Material 3 motion (community transcriptions, not the spec): duration tokens short4 = 200 ms, medium2 = 300 ms; emphasized-decelerate cubic-bezier(0.05, 0.7, 0.1, 1.0) for entering; standard-decelerate (0, 0, 0, 1); emphasized-accelerate for exit; entrance about 400 ms / exit 200 ms example — [Rust tokens port](https://docs.rs/crate/hydrolysis-m3/latest/source/src/theme/motion/tokens.rs); [Dart M3E](https://pub.dev/documentation/material_3_expressive/1.0.3/foundations_m3e_motion/M3EMotion-class.html)

### Inferences
- Factory proposal, a type scale for 1080p: 40 / 48 / 64 / 88 / 120 px (body/label/sub-head/headline/hero), ratio about 1.33, with Raleway weights 400-500 for body, 700-800 headlines; Raleway has old-style numerals by default: use lining numerals (font-feature-settings "lnum") for gauges, pressures and values (feature behaviour is general font knowledge, not sourced here).
- Spacing grid 8 px base, outer safe margin about 96 px (5%), 12-column grid.
- Photos: full-bleed with a scrim gradient (about 55-70% black to transparent behind text) or a duotone to brand colour; verify 4.5:1 against the worst pixel under the text via audit, not by eye. Never text over busy regions.
- Avoid template look: no identical card grids on every slide, no gradient-on-everything, no emoji/stock-icon decoration, no centred text blocks everywhere, vary layouts by slide function (claim+figure, full-bleed photo, sequence, comparison), keep one accent colour.
- Motion: entrance 250-400 ms decelerate (ease-out), exit 150-200 ms, no looping idle motion, stagger <=60-80 ms only to show real order, build order = reading/flow order, `prefers-reduced-motion` fallback = instant state.

### Gaps
- Primary sources for Refactoring UI numbers and Material motion spec not retrievable; no research on "AI-slop" look (opinion only); nothing on duotone/scrim contrast numbers.

## 5. Tablet task screens: touch targets and feedback

### Takeaway
Targets >=48 dp (Material) / 44 pt (Apple); 24 CSS px is only the WCAG AA floor. Explanatory (elaborated) feedback beats verification-only; immediate feedback suits hard tasks and novices.

### Cited Findings
- WCAG 2.2 SC 2.5.8 AA: 24x24 CSS px (or 24 px spacing); SC 2.5.5 AAA: 44x44 CSS px — [TetraLogical](https://tetralogical.com/blog/2022/12/20/foundations-target-size/); [Craft CMS](https://craftcms.com/blog/accessible-target-sizes)
- Apple HIG 44x44 pt; Material 48x48 dp (the 44 dp pointer figure was not verified; some pages wrongly state 44 px for Material or AA) — [Designer's field guide](https://www.designsystemscollective.com/a-designers-field-guide-to-wcag-ios-and-android-rules-31ba5d01d46a); [TetraLogical](https://tetralogical.com/blog/2022/12/20/foundations-target-size/)
- Shute 2008 (narrative review, not meta-analysis): formative feedback should be nonevaluative, supportive, timely, specific; verification-only is weaker than explanatory feedback (what/how/why); immediate suits difficult tasks and low achievers, delayed suits easy tasks and transfer (secondary summaries; verify in [Shute 2008 PDF](https://myweb.fsu.edu/vshute/pdf/shute%202008_b.pdf)) — [SAGE](https://journals.sagepub.com/doi/10.3102/0034654307313795); [evidence-based checklist](https://evidencebased.education/wp-content/uploads/sites/3/Feedback-checklist-1.pdf)

### Inferences
- On an 11-inch tablet (about 1600x2560 px at about 275 dpi, roughly 2.6-2.8 dp density; 48 dp is about 7-9 mm), factory proposal: primary targets 56-64 dp, min 48 dp, 8-12 dp gaps (Material convention, unverified here), hotspots on photos (tap-the-place) get an enlarged invisible hit area, at least 48 dp, and are placed so adjacent items do not overlap.
- Feedback on tap: instant (<=100 ms visual response), result state not by colour alone (icon + word, 3:1 contrast), then one or two sentences saying why the answer is right/wrong (misconception-specific), with the key part of the figure highlighted; allow retry for novices, and delay detailed review for the final check (transfer).
- Hazard tasks use ISO colours only in their safety sense; keep correct/wrong colours distinct for colour-blind users (blue/orange, per Okabe-Ito, plus icons).

### Gaps
- No primary Material/Apple text retrieved (fetch 404/no content); no effect sizes for elaborated or immediate feedback; no research on tablet-specific hit-area padding for photo hotspots.
