# Maritime, industrial-safety and explainer visual techniques

## 1. What do maritime/offshore providers' modules and demo screens look like?

### Takeaway
Public material is mostly marketing text. Maritime providers lean on 3D animation interspersed with video (OTG/Seagull/Videotel, Seably/KARCO), full-mission simulators with instructor stations and automated assessment (Kongsberg, Wärtsilä, GTT) and VR (Maersk). Almost none publish screen-level detail, so "what the screens look like" is largely a gap. Maersk itself warns VR does not fix weak objectives.

### Cited Findings
- Seagull and Videotel (merged 2020 as Ocean Technologies Group, later bought by Lloyd's Register) said they were investing in 3D animation and gaming technology; one trade report described core video material "interspersed with 3D animation and gaming type overlays". — [Seagull & Videotel: Under new management](https://splash247.com/seagull-videotel-under-new-management/); search summary of [oceantg.com](https://oceantg.com/videotel-is-now-otg/)
- Videotel's VR module "Wall Wash Test – Protecting Your Cargo" was built with OMS. — [Riviera](https://www.rivieramm.com/news-content-hub/virtual-reality-enables-immersive-training-57458)
- Seably (from April 2021) carries KARCO 3D-animated courses (e.g. pilot ladder, static electricity on tankers) that "clarify tricky concepts or complex processes"; offline-capable on PC and mobile. — [Maritime Executive](https://www.maritime-executive.com/article/seably-introduces-karco-3d-animated-online-marine-courses)
- Wärtsilä Cloud Simulation runs in a browser on OTG's Ocean Learning Platform (announced Sept 2021): instructor-led and self-directed exercises, sessions scheduled and recorded, per-person performance analytics. No screen detail published. — [Wärtsilä](https://www.wartsila.com/marine/products/simulation-and-training/cloud-simulation/otg-x-wartsila); [Wärtsilä news 2021](https://www.wartsila.com/media/news/16-09-2021-wartsila-cloud-simulation-now-available-on-demand-via-otg-s-ocean-learning-platform-3225847)
- Wärtsilä Land & Sea Academy mixes e-learning, instructor broadcasts, web simulators, VR, and 3D models beside real equipment (a full-scale RT-flex 3D model shows fuel injection and exhaust valve action; 2008 release). — [WLSA](https://www.wartsila.com/wlsa); [Wärtsilä 2008](https://www.wartsila.com/media/news/30-05-2008-new-simulator-for-electronically-controlled-marine-engines-installed-at-wartsila-land-sea-academy-in-switzerland)
- Kongsberg K-Sim Engine DEDF42 (dual-fuel ferry) LNG bunkering: shore-side interface for barge/tank/truck, fuel-quality monitoring (methane number, Wobbe Index, density), connect/disconnect, flow and purge control, ESD and overpressure scenarios; "3D walkthrough" of bunkering; instructor station with live alarm view, recording/replay for debrief, automated assessment for unsupervised runs. First model approved to DNV Class S for LNG-fuel training. — [Kongsberg 2025](https://kongsbergmaritime.com/feature_articles/2025/11/preparing-the-lng-workforce-for-a-cleaner-future/); [Ship & Bunker](https://shipandbunker.com/news/world/554879-class-approval-granted-to-kongsberg-digital-engine-room-simulator-for-lng-fuelled-vessels)
- K-Sim Engine L22 (MAN ME-GI LNG carrier): integrated control room/bridge panels, alarm handling, trends, power and gas management, ESD, up to 40 gas-detection sensors; roles split junior (basic rounds) / senior (emergencies, troubleshooting). — [Kongsberg L22](https://kongsbergmaritime.com/products/simulation/k-sim-engine/k-sim-engine-l22-man-me-gi-lng-carrier/)
- PC Maritime MED3D/PSV-3D use animated virtual switches, gauges and lamps; WinGD Xpert has a 3D engine room; K-Sim offers "3D BigView" and virtual walkthrough. — search summary: [PC Maritime brochure](https://www.pcmaritime.com/wp-content/uploads/2018/07/Brochure_MED3D.pdf), [WinGD](https://www.WinGD.com/en/digital-solutions/digital-training-solutions/w-xpert/)
- iPad "Engine Room Simulator - ERS" offers P&ID-style system diagrams with pan/zoom; ERS-01 is an open-source browser engine-room sim. — [App Store](https://apps.apple.com/us/app/-/id6767850469); [SourceForge](https://sourceforge.net/projects/marine-engine-room-simulator/)
- Maersk Training VR: hazard identification (experience consequences of failure), CO2 firefighting with home practice, ME/RT-flex engine training, mooring. Its own advice: start from needs analysis and objectives, "VR alone can't compensate for weak learning objectives". PwC figures it quotes (4x faster, 43% fewer injuries) are second-hand and unverified. — [Maersk Training](https://maersktraining.com/news-and-insights/news/virtual-reality-hype-reality-and-value-in-maritime-and-offshore-training)
- GTT/DNV/ABS membrane-tank courses (Mark III, NO96) are instructor-led; GTT's G-Sim cargo simulator is DNV-approved, classroom or cloud. — [DNV](https://dnv.com/training/lng-carriers-11527); [ABS brochure](https://ww2.eagle.org/content/dam/eagle/publications/ABS%20LNG%20Academy%20Brochure.pdf)

### Inferences
- The competitive pattern is "instructor station + recorded replay + auto-assessment", which our instructor-projects/trainee-tablet split already mirrors; a replay or log of trainee actions would be a cheap parallel.
- Role-tiered scenarios (junior = rounds, senior = faults) suggest tagging tasks by competence level.

### Gaps
- No screenshots or demo descriptions found for Videotel/Seagull, Marlins, MarineLearn, Unitest, MAN PrimeServ, SIGTTO, Shell/BP, Viking, ABS/LR e-learning. No evidence either way on hotspot-style tasks. Search tool returned marketing text only; browsing their demo portals directly would be needed.

## 2. Industrial safety: 3D walkthroughs, spot-the-hazard, LOTO, P&ID, pipe colours

### Takeaway
Commercial LOTO/hazard products are decision-and-drag simulations in a realistic scene. Government free tools (OSHA) use scenario inspections. I found no source on ISO 14726 colour-coding used as teaching device.

### Cited Findings
- Vector Solutions "Safety Challenge: Spot the Hidden Hazards": gamified; drag-and-drop, hazard hunts, scenario decisions; learner finds and fixes hazards before LOTO begins. — [Vector](https://www.vectorsolutions.com/courses/safety-challenge-spot-the-hidden-hazards/)
- HSI LOTO Simulation: ~10 min, learner locks and tags equipment across scenarios. — [HSI](https://hsi.com/courses/lockout-tagout-simulation)
- OSHA's free LOTO tool: seven simulated inspections, decisions from on-screen information. — [OSHA](https://www.osha.gov/etools/lockout-tagout)
- Amatrol LOTO: 3D animations, video, photos, voice-over, interactive exercises. — [Amatrol](https://amatrol.com/product/loto-online-training-course/)
- FreeRangeXR VR LOTO: pick the right lockout devices, isolate energy sources, notify personnel, graded on a hydraulic pump scenario. — [PixoVR](https://pixovr.com/vr-training-content/lock-out-tag-out-freerangexr/)
- Coggno/360 Immersive LOTO VR: identify energy sources and which device applies; SCORM. — [Coggno](https://coggno.com/online-courses/osha-compliance/loto/lockout-tagout-loto-vr-activity)

### Inferences
- The shared structure is "find the energy source / hazard in a realistic scene, then apply the right device in the right order, graded": maps directly to our tap-the-place and sequencing tasks on real photos.
- Feasible on tablet: photo hotspots, ordered-step tasks, "isolate before you touch" order checks. VR is not needed.

### Gaps
- No source found for ISO 14726 pipe colour-coding in training, P&ID animation products, or Kongsberg/Wärtsilä mimic-panel looks.

## 3. Technical explainers: what makes them clear

### Takeaway
The strongest explainers share a small kit: draggable 3D model, one slider per physical variable, consistent colour per part/force, cutaways and part hiding, linked plot, and pause control. Interaction answers one question at a time.

### Cited Findings
- Ciechanowski, Mechanical Watch: parts added one at a time (assembly sequence), semi-transparent parts, cut-aways (hole in barrel lid), drag-to-rotate, sliders (wind spring, scrub time, gear speed, zoom to microscopic scale), buttons for discrete states, each named part has a fixed colour that the text refers to, active gear pairs highlighted, arrows for rotation/force, a credit-card outline for scale, global pause. — [ciechanow.ski/mechanical-watch](https://ciechanow.ski/mechanical-watch/)
- Ciechanowski, Internal Combustion Engine (2021): cross-section views marked with diagonal hatching, hide surrounding parts, crank-angle slider driving piston, animated four strokes with global pause, cam sliders linked to a valve-lift plot, colour change for mixture vs exhaust, black dots on timing gears to show 2:1 ratio. — [ciechanow.ski/internal-combustion-engine](https://ciechanow.ski/internal-combustion-engine/)
- Ciechanowski, Naval Architecture: sliders for hull proportions, cargo, liquid level, waves; colour-coded force vectors (pressure, buoyancy, gravity, net); stable/unstable heel zones in colour; centre of buoyancy and metacentre markers; guide lines for righting arm; righting-arm plot linked to heel; inline toggles (empty/full tank, with/without weight); label colours tied to matching objects. — [ciechanow.ski/naval-architecture](https://ciechanow.ski/naval-architecture/)
- Ciechanowski, Moon (2024): ghost trails, markers dropped at points, side-by-side space view and observer view, realistic vs exaggerated scale toggle, Earth made transparent. — [ciechanow.ski](https://ciechanow.ski/)
- Distill "Communicating with Interactive Articles" lists: animation (state change, causality), sandboxed simulations, multiple representations of one idea, prediction prompts ("You Draw It") before the answer, low-stakes quizzes with feedback, segmenting (play/pause/scrub), details-on-demand and hotspots ("overview first, zoom and filter, then details"), step-based slides contrasted with scroll layouts. — [Distill](https://distill.pub/2020/communicating-with-interactive-articles/)
- Bret Victor coined "explorable explanations": reactive documents with explorable examples; Nicky Case defines an explorable as one that teaches and is "more interactive than a boring ol' quiz". One critique: widgets that drop the reader in a sandbox with "figure it out" are not explanations. — [Victor](https://worrydream.com/ExplorableExplanations/); search summary of [datastori.es #103](https://datastori.es/103-explorable-explanations-with-nicky-case/)
- Sketchfab annotations: numbered pins on the model; Next/Previous buttons fly the camera between them (work even with pins hidden); deep link to a given annotation with `?annotation=x`; Markdown text. — [Sketchfab help](https://help.sketchfab.com/en/articles/16152328)
- Animagraffs (Jacob O'Neal): animated cutaway infographics of engines, firearms, displays; one source says made in Blender. Sources disagree on method (older GIF era vs newer 3D cutaways); no first-party description found. — [Gigazine](https://gigazine.net/news/20140703-animagraffs/); [GeekNews](https://news.hada.io/topic?id=24696)

### Inferences
- Persistent colour-per-part with text coloured to match is the cheapest, biggest clarity win.
- Hatched cutaway marking plus hide-neighbours is the convention to copy for tanks, valves, pumps.
- A single "pause all motion" toggle also helps projector use and tablet battery.

### Gaps
- Could not verify Pudding, NYT or Reuters scrollytelling specifics on ships/ports (searches returned only a Washington Post Ever Given graphic via FlowingData and an unspecific Reuters mention). Animagraffs and Engineering Explained techniques are second-hand only.

## 4. Ideas to adopt, with feasibility on a Yoga Tab 11 (plain HTML/SVG/three.js)

Feasibility is my judgement from the sources, not tested. Tablet 3D performance memory in the factory notes says SVG flows are the bottleneck, not 3D.

- Colour-per-part and colour-per-force with matching text spans (Ciechanowski). Easy, SVG/CSS, zero cost.
- Step scrubber / sliders for one variable (valve opening, tank level, heel angle) driving a flow animation plus a linked small plot. Easy-medium; plot is a cheap SVG path.
- Cross-section hatching and "hide the rest" toggle in three.js (clipping plane or layer toggle). Medium; two-material clipping is light. Pre-bake hatching to a texture.
- Ghost trail / dropped marker for gas path (SVG polyline with fading dasharray). Easy; avoid filters while moving (our L65 law).
- Numbered annotation pins with Next/Prev camera fly (Sketchfab). Easy in three.js, one tween per step; doubles as instructor "Next".
- Assembly-by-steps (add one part per Next press) for equipment build-up and procedure order. Easy, toggles visibility.
- Prediction prompt before reveal (Distill "You Draw It", tap where gas goes first). Easy; fits tablet tasks.
- Paired views: 2D schematic and 3D equipment, highlighting the same part in both. Medium; shared ids.
- Hazard-hunt on real photos then apply correct isolation in order (Vector/OSHA/FreeRangeXR pattern). Easy.
- Scale toggle realistic vs exaggerated (Moon), credit-card-style scale reference. Easy.
- Instructor-side recording/replay and auto-assessment (Kongsberg). Medium; log trainee taps with timestamps.
- Not worthwhile on tablet: full VR, live mimic-panel simulators (needs a process model), Thauma-style video unless the gap is big.
