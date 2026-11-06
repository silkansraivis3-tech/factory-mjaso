# NOVIKONTAS factory decks: current baseline (local files only, factory 2.78.0, 2026-11-02)

Paths are under `C:\Users\aleksisv\Desktop\Novikontas factory\plugin\skills\` ("S/") unless noted. Facts only.

## 1. Slide types, layouts, components

### Takeaway
Every compiled slide is one of 13 owner-reviewed templates (L61) with a variant, plus a compose vocabulary of ~8 compositions, cards, a recap and photo screens. Two modes: light (default) and dark/photo, chosen per slide.

### Cited Findings
- 13 templates, each with variants: explain-figure (figure-right/left/text-only), figure-stage (figure/figure-top), photo-explain (full/split/column), compare-two, procedure (with-figure/figure-left/text-only), task-launch (tablet/room/check), recap (cards), opening (statement/photo), long-explanation (model/figure-left), three-content-blocks, reference-table, reading-with-figure, content-in-parts — S/course-module-ui/knowledge/layout-templates.json:20-33
- Compositions on `.slide-body`: opener, ordinary flow, two-col (+wide-left/right), stage, activity, checkbody, sum, recap, plus `.statement`+`.support`, `.trio`, `data-compose="sparse"` — S/course-module-ui/references/vocabulary.md:46-67
- Compiled extras: `.copy`, `.box`/`.call`, `.inset` (small real photo), `.legend` (numbered row), `.slide.photo.split`, `.act-photo`, `.aside`; `.cur`/`.lit` mark the line a stepping figure is on (amber = "here now") — vocabulary.md:69-86
- Content-in-parts: `.lt-parts/.lt-tabs`, Next walks parts of ~75 words; `.lt-tiles` (several photos, each opens full screen), `.lt-strips`, `.lt-table`, `.lt-compare` — vocabulary.md:33-39; layout-templates.json:16
- Photo screens: `.photo-wrap`, `.photo-scrim`, `.photo-copy`, `.photo-badge`, numbered `.support.seq`, `.credit`; photo screens always dark — vocabulary.md:90-99
- Blocks: `.cards` c2/c3/c4 ("never one, never five"), `.card.key/.step/.warn/.good`, `.law`, `.warnbox`, `.fin`, `.meta`, `.steps`, `.tbl`, `.takeaway` (one per screen max, amber left rule), `.frag` reveal — vocabulary.md:103-120; anatomy.md:114-127
- Header band `.slide-kind`: full-bleed navy, uppercase, .14em tracking, names the KIND of screen; footer strip; progress; overview grid; landing screen — anatomy.md:31-50; vocabulary.md:136-146
- Recap slide (L51): one design every module, boxes rise in one by one, blue-to-amber rule draws across, then "next" strip; 3-6 points — vocabulary.md:59; gb_compose.css:850-852
- Quiz in deck: `.quiz` with `.q-opt.right/.wrong` and `.q-why` — vocabulary.md:129
- Deck engine `gb_deck.js`: Start, Next/Prev, progress, overview grid, instructor cue (`data-cue`, hidden), fullscreen, keyboard, guarded swipe, idle chrome, per-screen hooks, figures that step take Next/Back first, lv/ru/en control words; ES5; red banner if nav controls missing — S/course-module-ux/assets/gb_deck.js:1-45
- Slide entry animation: `slideIn` 0.38s translateX(26px)+fade — S/course-module-ui/templates/gb_shell.css:218; anatomy.md:27
- Every picture opens full screen (`gb_zoom.js`): tap, pinch/double-tap/+- zoom, close by X/tap/Esc/swipe-down/Back; carries photo record (part shown, what, credit) — vocabulary.md:218
- Step runner (`gb_run.js`) on START_HERE: one step at a time, progress bar, one primary button, Back/Next, stored step; "bar mode" returns from task to deck screen — S/course-module-ux/assets/gb_run.js:1-25. Architecture: one HTML, Start, Next to end; zero `<a href>` in slides — S/course-module-ux/SKILL.md:13-30
- Varied look rule (L62): no two adjacent slides same shape+ground; shapes: picture-right/left/top, photo-full, photo-framed, text, task, recap, opening, comparison; ≥80% light slides, ≤20% dark — docs/FACTORY_LAWS.md:575-584; layout-templates.json:14
- Word budgets measured: 85 beside a picture, 70 with inset, 50 full/framed photo, 70 under top photo, 75 per part; dense = >60 words must have a picture; never >2 teaching slides in a row without a teaching visual — layout-templates.json:13-19

### Inferences
- Interaction on slides is instructor-driven (Next/steps/tap a lit line or a 3D part); no scroll-triggered, branching or learner-paced slide navigation exists.

### Gaps
- Not inspected a built deck in a browser; list is from specs/CSS/docs.

## 2. Design tokens, type, projector/tablet targets

### Takeaway
Brandbook-locked palette and Raleway; type in `clamp(…vmin…)` with a 12.5 px floor; one logical 1280x800 stage scaled by vmin.

### Cited Findings
- Fonts: Raleway (bundled variable TTF, OFL, offline) + Segoe UI fallback; mono Cascadia/Consolas — S/course-module-ui/knowledge/tokens.json:140-146; vocabulary.md:24-27
- Colours: navy #0A2463, deep #0A182E, blue #2EB6F8, blue2 #53A7DB, steel #415C8F, amber #E9A51E, ink #011111, grey #E7EBF0; good #12805A/#4FD6A0; warn #B4453A/#FF8C82; cold #8FC2FF — tokens.json:8-123
- Layout templates restrict to brandbook colours (Navy, Novikontas Blue #53A7DB, Pitch Black, Steel Blue, Light Grey, White; paper #F7F8FA, deep #06173D; the old amber replaced by Blue) — gb_layouts.css:36-47; layout-templates.json:9
- Radii 20/13/8 px ("three radii, no fourth"); shadows `--sh`, `--sh-d`; cards 1px line + padding min(2.6vmin,26px) — tokens.json:128-139; anatomy.md:70-84
- Type scale in layouts: title clamp(28px,5.75vmin,62px); body `--lt-fs` clamp(15,2.5vmin,30); lead clamp(16,2.6vmin,31); opening title clamp(34,8vmin,86); activity code clamp(64,19vmin,200) — gb_layouts.css:53-54,123,290,301
- Spacing: top min(10.5vmin,84px), pad-x min(8vmin,64px), gap min(4vmin,32px); text/visual split default 55/45 (50-60) — gb_layouts.css:49-52; layout-templates.json:12
- Stage: one logical 1280x800 slide, 1 vmin = 8 px — layout-templates.json:7. Sign-off viewports 1366x768, 1024x768, 800x1280 (primary tablet, portrait), 360x740 — S/course-module-ux/measure/knowledge/floor.json:42-47. Figures checked at 1280x800, 1024x768, 1920x1080 — FACTORY_LAWS.md:451
- Official logo ~10.5 vmin tall top right; white version on dark/photo slides — FACTORY_LAWS.md:576
- Floor: text ≥12.5 px (SVG effective px), contrast AA 4.5/3.0, targets ≥44 px, no slide scroll ("no scrollbar at all"), no h-scroll, 0 console errors — floor.json:4-40
- Never hardcode colour in new work; raw colours in SVG fill/stroke are content — S/course-module-ui/SKILL.md:72-96
- Hazard colours (red/flame/toxic) NOT in the token set; owner decision open — tokens.json:180-182

### Gaps
- Projector target 1920x1080 is only named as a test size (one mention); canonical frame is 1280x800 / 1366x768.

## 3. 2D figure kit and 3D kit

### Takeaway
Figures are JSON specs, not hand drawings: 2D `kit.json` (~60+ parts in 7 families) and 3D `kit3d.json` (34 parts), both with built-in labels, steps, fullscreen, performance rules.

### Cited Findings
- 2D kit: parts incl. panel, level, gauge, readout, valve, pipe (flow fill), tank (burst), pump, engine, exchanger, ga (ship), zone, scale (draggable marker), curve_chart (draggable point, log axis), molecule, gas_cloud (drift), spray, fire, person (PPE), airlock, hatch, flammability diagram, tree, step_track etc. — S/course-visuals/kit/SPEC.md:64-127
- Seven families: Instruments, Piping/flow, Ship/spaces, Cutaways, Gas/fire/machinery, Charts, Procedures — SPEC.md:259-267
- Animation types: stepped `play` [part,to,ms,delay,ease(inout/linear/out)], marks that fire alarm(amber)/trip(red)/limit(grey) as value crosses, `then` reactions, replay/prev, reduced-motion jumps to end — SPEC.md:187-212
- Kit does by itself: collision-free label placement (4 px clear), 12.5 px floor by growing type, boxes sized to words, zoom-to-fill frame, light/dark panel mapping — SPEC.md:33-49
- A lit slide line is a tap target that plays that step — SPEC.md:289-293
- Task mode: same spec drawn still on a task page (kit_step, unlabel, tappable parts) — SPEC.md:269-277
- Look (L63): physical equipment drawn in material with light/shade/real features; screens stay calm ISA-101 HMI (grey/blue at rest, amber alarm, red trip) — SPEC.md:294-321
- Meaning checks: BLOCK/NOTE findings (NAMED, LOOSE END, INSIDE, NO GAS, AIM, LEADER, GRID, STEP, LABEL, TRUTH); "never a box" for machines (gvu, switchboard, motor, propeller, lng_truck) — SPEC.md:76,155-185; commit e3ae2eb
- Patterns library: ship_ga, bunkering_line, vent_system, fuel_supply, engine_modes, fuel_types, fuel_space_access — SPEC.md:224-253
- Smooth-motion rules (L65, 2.78.0): baked shadows when at rest, own layer `will-change`, no CSS/SVG filter or mask on moving drawings, gradient fills for soft edges, mask only while fluid front part-way; never `overflow:hidden` (4 fps) — SPEC.md:323-336; audit_motion.js
- Measured: Yoga Tab 11 flow drawing 32-43 fps before fix; 3D runs 56-60 fps full light on the tablet; real-tablet result of 2.78.0 not yet measured — SPEC.md:325; memory `tablet-3d-performance.md:11,15`
- 3D kit: three.js r128, ACES tone mapping, studio light, one sun shadow, see-through ghost walls and cut-aways; labels on parts (amber dot, white pill) auto-avoid each other; tap part = glow + camera frame; label is a button; steps walked by deck Next/Back (750 ms tween); controls (toggle/select/step, 56 px); captions; Labels on/off; full screen; built ahead on previous slide; poster fallback; reduced-motion; context-loss survival — S/course-visuals/kit3d/SPEC.md:13-38,123-149
- 3D auto-lite: `light:"auto"` drops shadows/studio light on judder (>30 ms) and remembers device — kit3d/SPEC.md:79
- 3D parts: hull, deck_plate, room, enclosure, tank_c/sphere/prism, pipe, pipe_dw (cut open), valve (relief), flange, coupling, hose, vent_mast, vessel, cabinet, engine, pump, esd_button, detector, person, dimension, limit_box, zone, gas (rise/sink/spread/plume, fuel colours), arrow, flow — kit3d/PARTS.md:14-76
- 3D colour rule: gas yellow, cold pale blue, red = handwheels/shutdown, amber only label dots/limits/zone 1, blue only selection; 3-9 labels/step; true proportions — kit3d/SPEC.md:151-162
- Laws: 3D at most half the slides (L46); at least one per module where subject allows, never instead of a wanted photo (L60); 30 fps with CPU 4x slowdown — FACTORY_LAWS.md:367-372, 530-543
- Instructional-animation law (L13/L20): motion must explain mechanism/flow/state/sequence; categories teaching/affordance/ambient/chrome (`data-motion`); max one ambient effect per screen; four questions gate; rejected patterns: random floating, decorative pulsing, bouncing icons, fade-ins, moving arrows w/o process, infinite loops, parallax, spinners; reduced-motion, 44 px controls, no hover-only — S/course-visuals/review/knowledge/motion-rules.json:6-89; FACTORY_LAWS.md:125-139
- Figure "alive" classes MOVES / RESPONDS / STATIC (static = defect) — FACTORY_LAWS.md:125-131

## 4. Trainee task types

### Takeaway
19 answer mechanics + 10 interactive types (Part A/B), none involving typing; all graded by `data-key`; one shared engine.

### Cited Findings
- Choose one, choose all, choose-and-justify, order, match, categorise, cloze, hotspot, label_diagram, spot_the_hazard, read_instrument, set_value (slider/dial), panel_operate, scenario (decide, see consequence, decide again), find_the_fault, spot_the_error, build_the_plan, timeline (order then tap stop point), compare — S/course-factory/knowledge/media-and-tasks.json:66-103
- Part A (check): true_false (flick card), "how sure are you" confidence, cause-and-effect chain. Part B (challenge): calculate, predict (drag point then real curve draws), explore (live model with sliders), investigate (pin evidence), critique, line_up (3D deck valves, start pump), inspect_round (3D room / 360 photo), take_apart (3D), test_atmosphere (4-gas meter simulation) — media-and-tasks.json:104-124; S/course-task-ux/SKILL.md:211-263
- Rules: first-try screen, every drag also tap-tap, hand-gesture hint once, controls ≥56 px, question ≥18 px, instant feedback, animated score ring, no timers, wrong answer = hint + brief reason not revealing answer; right answer shown only in debrief by instructor; self-check answered once — task-ux/SKILL.md:118-151,230-237
- Rejected as only way: double-tap, long-press, swipe, pinch — media-and-tasks.json:131
- No pass mark on module checks (only the final assessment) — memory `igf-review-2026-10-21.md:13`

## 5. Laws and audits limiting the look

### Cited Findings
- Module 1 `:root` is the reference; palette/type/header/card/pill/takeaway locked, but not layout or screen count — course-module-ui/SKILL.md:46-70
- L17 every screen intentionally composed; `audit_compose.js` measures ink/centroid/dead half (COMPOSED/REVIEW/WEAK) — SKILL.md:123-154; course-module-ux/SKILL.md:251-282
- L53 no empty space; figure fills frame (≤half blank, no blank piece >1/5); words at reading size; L54 every drawing whole, 4 px label clearance — FACTORY_LAWS.md:438-463
- L22 no internal shorthand, version control, honesty markers or IMO model course citations on slides — FACTORY_LAWS.md:156-180
- L52 as many real photos as possible; no AI picture of equipment trainees must recognise (L33); photos ≥1600 px (≥800 minimum), every photo used once (L58), credits off slide into full-screen record (L56) — FACTORY_LAWS.md:423-436,509,585-590
- Audits: audit_deck, audit_collide, audit_compose, audit_motion, audit_drawing, audit_drive (walks every step), audit_opacity, verify_figures, check_navigation, audit_ui.py (raw colours, off-canon tokens, undefined classes/vars) — S/course-module-ux/measure/scripts/run_audits.py:7,46-49; course-module-ui/SKILL.md:170-180
- L26: the person may override any look/behaviour rule after one warning; recorded and never reverted — course-module-ui/SKILL.md:16-23
- Paperless, ES5 shared engines, tablet first, `:has()` mirrored with class — course-module-ux/SKILL.md:120-130

## 6. Known weaknesses and review feedback

### Cited Findings
- IGF instructor review (2026-10-21): "A lot of dark slides" (-> 80/20), credits on slides, text layout, icons, clickable ship plan -> real photos; hand-drawn diagram called "bad diagram: pastel boxes, tiny pale labels" — memory `igf-review-2026-10-21.md:11`; S/course-visuals/kit/SPEC.md:235-237
- Owner (L62): 29 of 33 slides one layout, "hurts the eyes"; pixelated photos; logo too small — FACTORY_LAWS.md:575-576
- Operator on M01 s04: visual too big with empty space, info too small, buttons not clickable — FACTORY_LAWS.md:444-446
- Full-build review (2.56.0): real photos in tasks only 7 in whole course; spaces (tank connection space etc.) exist only as drawings; library photos "roughly fit" (ferry for bunkering); learner-active time M01 32% vs 80% target; M03 lost its 3D scene — _claude/REVIEW_IGF_FULL_BUILD_2026-10-20.md:60-72
- 3D kit early review: factory scene "bare pipe", chips not pointing, small in big panel; 11 labels colliding in one view; remaining gaps: M04 cloud shapes, M07 zone 0 as skin, M15 no legend; no gauge part in 3D — _claude/CONTEXT.md:316-347
- Tablet performance: flow animations (SVG stroke-dashoffset) were the bottleneck, 2.78.0 fix unmeasured on device — memory `tablet-3d-performance.md:11-15`
- Known token drift: modules 03/05/06 second dialect; no hazard colours — course-module-ui/SKILL.md:196-213
- Own admission: shipped reference deck carries 134 raw chrome colours, token set only partly adopted — course-module-ui/SKILL.md:86-90
- Kit weaknesses stated: parts "still planned": tank types A/B/C, flowchart, cause-and-effect matrix — kit/SPEC.md:264,267
- Honest limit: factory 3D is "geometry the factory can state exactly", not the look of named equipment; real scan/licensed models are separate (model_3d_scan, model_3d_licensed) — media-and-tasks.json:42-48
- Static check can't see runtime-built figures; human review required — _claude/CONTEXT.md:309-310

### Gaps
- No analytics on trainee engagement or instructor reaction to animation quality found locally.
- The IGF triage file (`Desktop\M01M02_v262\REVIEW_IGF_Basic_2026-10-21_triage.md`) not found; only the memory summary was read.
- No built deck screenshots inspected (read-only spec research).
