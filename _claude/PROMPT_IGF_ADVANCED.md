You are building the NOVIKONTAS **IGF Advanced** course with the Course Factory, as a new course. Aleksis Vejs owns the IGF courses. In Aleksis's own words: "šis ir IGF Advanced, nākamā pakāpe tam ko tu jau taisīji, tāpēc būtu jābūt ok un arī knowledge base jau ir. Te gan ir svarīgi, ka tiek izmantots simulators." It is the next level of IGF Basic, which is already built. The knowledge base exists. **The simulator must be used.**

## The course (locked - change delivery, never content)
- "Paplašināts apmācības kurss darbam uz kuģiem, uz kuriem attiecas IGF Kodeksa prasības". STCW A-V/3-2 (STCW V/1-1), IMO model course 7.14.
- Programme: LJA standard programme **13-51-307, version 3 (15.10.2025)**, 17 pages, Latvian:
  `C:\Users\aleksisv\Downloads\13-51-307_Paplasinats-apmacibas-kurss-darbam-uz-kugiem-uz-kuriem-attiecas-IGF-kodeksa-prasibas-15_10_2025-logo (1).pdf`
  (the same file without " (1)" is also there). Read the whole PDF yourself. The figures below are a summary, not the source.
  - **40 academic hours (40 min each) in total, final exam included.** At most 11 ac. h a day, so about 4 days.
  - The training plan (section VI) has **29 topics + topic 30, the final exam**. Its hour columns are EMPTY: the training centre splits the 40 hours, theory vs practice, so that the 29 planned outcomes (section II, one per topic) are reached. Propose the split (by weight in IMO MC 7.14, the old course and the simulator time needed) and show the reasoning. Never pad or cut a topic.
  - Topics, in short:
    - 1 chemistry/physics (13 subtopics: boil-off and weathering, critical point, flammability, SVP, bubble point, hydrates, methane number...), 1.3-1.8 thermodynamics, materials, brittle fracture;
    - 2 SDS; 3 ship power plants; 4 auxiliaries; 5 technical terminology;
    - 6 ship design, fuel systems by engine type, storage, insulation, pumps, piping, expansion, flame screens, temperature / level / pressure monitoring, cryogenic pressure control, inert gas and N2, gas detection, ESD;
    - 7 fuel system theory: LP / HP pumps, vaporisers, heaters, compressors;
    - 8 tank procedures and checklists: inerting, cool-down, first fill, pressure control, warming, gas-freeing;
    - 9 bunkering and storage data; 10 ship-supplier communication (terminal / truck / ship); 11 safety and emergency procedures;
    - 12 bunkering operations, emergencies, ship-shore and ship-ship communication, rollover;
    - 13 measurements and calculations (filling limit, OBQ, ROB, consumption);
    - 14 safe management at sea and in port; 15 pollution effects; 16 spill / leak / venting response; 17 MARPOL, IMO instruments, guidelines, port rules; 18 IGF Code;
    - 19 hazards (flammability, explosion, toxicity, reactivity, corrosion, health, inert gas, static, pressure, cold);
    - 20 gas detection calibration and use; 21 consequences of non-compliance; 22-23 risk assessment; 24 safety plans and instructions;
    - 25 hot work, enclosed spaces, tank entry, permits; 26 safety and rescue equipment (BA, PPE, resuscitation, rescue); 27 work safety (maintenance precautions, IEC 60079-17, ship-shore checklist);
    - 28 first aid per SDS; 29 fire detection and fighting;
    - 30 final exam.
  - **At least two bunkering operations on the simulator** (section III item 3 and the sea-service footnote: two of the three required bunkering operations may be replaced by simulator training in this course).
  - Assessment: 90 % theory and 100 % practice attendance. A test needs **at least two variants, each with at least 3 questions per planned outcome** (29 outcomes, so 87 or more a variant). Pass mark 70 %; one retake. Practical tasks are marked by written criteria (annex 6).
  - Groups: 24 trainees in theory, 8 per instructor in practice. Entry: an IGF Basic COP (A-V/3-1).
  - Sections VIII-X (rooms, equipment, literature) and annexes 1-6 are templates for Novikontas to fill. Draft them from what the course really uses (the simulators, the KB documents, the decks), and mark them for Aleksis to check.

## Where things are
- **Factory:** `C:\Users\aleksisv\Desktop\Novikontas factory`. Plugin `course-factory` **2.72.7**, on main and installed.
  - Read `00_READ_ME_FIRST.md` and `CLAUDE.local.md` first.
  - `_claude/CONTEXT.md` is large: Grep `^##` first, then read only the sections you need.
  - Use the `course-factory` skill in new-course mode and follow its laws: approval gates for the architecture, the ILO map and each module script; real photos first (L58); 3D once per module where it fits (L60); the exercise slide; the meaning checks on figures (a part where it really is, connected, the words match the picture).
  - Build with the workflow (`build_course.js`): waves of 3, builders and QA as it sets them.
- **IGF Basic (the level below; reference only, NEVER edit or run tools on it):** `C:\Users\aleksisv\Desktop\Kursi\Drošības pamatkurss`.
  - Read its `CLAUDE.md` and `course/working_claude/COURSE_STATE.md`.
  - Copy its folder layout, course language and look.
  - Advanced builds on Basic and never re-teaches it. Where a topic repeats a Basic subject, go one level deeper (operate, calculate, decide, lead), and say which Basic module it builds on.
- **Gas Advanced - the reference for what an ADVANCED course looks like** (shared Drive folder "gas advanced", owner Raivis):
  https://drive.google.com/drive/folders/1oek6DPYls76_LCr7SZRg6VOXpSquQkU0 (id `1oek6DPYls76_LCr7SZRg6VOXpSquQkU0`).
  - It is "Advanced Training for Liquefied Gas Tanker Cargo Operations", STCW A-V/1-2-2: 19 module folders (`module01`...`module19`), `_course_shell`, `COURSE.html` (53 ac. h), built with this factory.
  - It is not on `G:` unless Aleksis has added a shortcut to My Drive (look for `G:\My Drive\gas advanced` first). Otherwise list it with the Google Drive connector and copy only what you need into a staging folder in My Drive (it then shows under `G:\My Drive\...`).
  - Use it for:
    - how a 50-hour LJA programme was split into modules;
    - the depth of an advanced course;
    - how the simulator, calculations and procedures were taught;
    - the subjects the two courses share (gas properties, ESD, gas detection, SDS, PPE, first aid, firefighting) - reuse its proven figures and photos, adapted from cargo to fuel;
    - its pictures, already in the Gas Library as `kb-gas-advanced` (188 images).
  - **Its instructor feedback** (Google Doc "Feedback" in that folder, by Kamila Jasvina, id `1V7sEHjpx6CP2uXvX-JYRtcp_uZWR8ApR7Q7o227_Vqg`) is the list of mistakes NOT to make again. Read it whole. In short:
    - instructor notes and cues must not reach the trainee tablet;
    - figures must scale (many "scale issues");
    - every button, GIF and picture must work and open on the tablet (no frozen GIF, no white window);
    - facts must be right (propane flashpoint -104 °C);
    - a label must not run into the next item (Invar: "36 % nickel steel");
    - use real certificates and documents, not AI pictures ("looks like a game for kids");
    - arrangements must be right (compressor and motor rooms near the accommodation, the drip tray shown);
    - today's technology (ME-GI / ME-GA, DFDE / TFDE, not steam turbines);
    - the right names on schemes ("vent mast", not "last resort");
    - show the real equipment as well as the animation (PERC);
    - never show equipment Novikontas does not have (ammonia detection tubes);
    - SDS, not MSDS;
    - a scheme rather than an AI GIF for displacement and dilution.
- **Knowledge bases:**
  - IGF KB: `C:\Users\aleksisv\Desktop\Kursi\Drošības pamatkurss\KNOWLEDGE_BASE` (IGF Code 2016 and amendments, MSC circulars, the methanol, ammonia and hydrogen guidelines...).
  - Gas Advanced KB: `...\Drošības pamatkurss\knowledge_base_existing\gas-advanced\KNOWLEDGE_BASE`.
  - KB builder: `C:\Users\aleksisv\Desktop\Kursi\COURSE_KB_BUILDER`. Use it to add the simulator manuals and IMO MC 7.14 where page-cited text is needed.
- **Shared Gas Library:** `G:\My Drive\Gas Library`. Read its `CLAUDE.md`.
  - `python tools/find.py "<subject>"` FIRST for facts, pictures and documents.
  - Copy pictures with `tools/use_asset.py` (provenance goes with the file); save finds with `tools/contribute.py`.
  - `igf-advanced` is listed as planned in `library_config.json`. Register it with `contribute.py register-course igf-advanced ...` once modules exist.
- **Simulator manuals** (`G:\My Drive\Gas Library\documents\manual\`, INSTRUCTOR_ONLY, never on the tablets):
  - LNG bunkering: `LCHS-5000_LNG_Bunkering_Trainee_Manual.pdf`, `TechSim5000_LNGBunkering_PLSpec_November2019.pdf`.
  - Methanol bunkering: `LCHS 5000 TechSim Methanol Bunkering Simulator Trainee Manual.pdf`, `TechSim5000_MethanolPac_PLSpec_May2025.pdf`.
  - Dual-fuel engine room: `ERS-TechSim_LowSpeedEngine_DFTanker_Trainee_Manual.pdf`, `DualFuel-DieselElectric_(2019_Wartsila).pdf`.
  - Gas detectors: `DRAGER X-am 2500.pdf`, the Dräger handbook.
  - Also `documents\publication\Safe handling and bunkering of Methanol.pdf`.
  - Novikontas runs the Wärtsilä / Transas LCHS-5000 / TechSim LNG and methanol bunkering simulators and the ERS dual-fuel engine room. Factory law L28: assume every simulator is available, never ask.
  - Design the simulator exercises from these manuals:
    - at least the two bunkering operations (one LNG, one methanol is a good pair);
    - simulator work wherever a topic suits it: tank cool-down and pressure control (8), fuel gas supply and changeover (6-7), ESD and leak response (11, 12, 16), measurements and calculations on the simulator's own data (13).
    - Each exercise gets trainee and instructor descriptions with marking criteria (annex 6).
    - Count the simulator hours in the 40.
- **The old IGF Advanced course** (factory law L41: the old course is the foundation):
  - Google Drive folder `IGFa_15.09.2025`, id `1JjCcGQ_v5M7QDbwIeIzGVCFs81mvC_sV`: 9 chapter decks (pptx, up to 71 MB), exercises E-1...E-11, Day 5 Methanol, tests, test pictures `IGF Advance 1-4.jpg` in `10. Test`.
  - Inventories with file ids: `G:\My Drive\Gas Library\_inventory\DRIVE_INVENTORY.md` (section "## 2. IGFa_15.09.2025") and `DRIVE_INVENTORY_2026-10-23.md`.
  - It is NOT on `G:`. Copy files with the connector's `copy_file` into a staging folder in My Drive (e.g. `_staging IGF Advanced old course`); they appear under `G:\My Drive\...` in a minute or two. Never pull a big file through base64.
  - For each part, record keep / modernise / add.
- **New course folder:** `C:\Users\aleksisv\Desktop\Kursi\Paplašinātais kurss IGF`.
  - Lay it out like IGF Basic: `course/` as its own git repo (local commits are fine), `source_files/` with a copy of the programme PDF, and a `CLAUDE.md` modelled on IGF Basic's.

## Order
1. **Intake.** Read the programme, IGF Basic's state, the Gas Advanced structure and feedback, the old course inventory and the KB.
   - Write a short source map: each of the 29 topics against its sources (KB documents with pages, old-course chapter, Gas Advanced module, simulator manual).
   - Note gaps and source conflicts. Never pick one side of a conflict silently.
2. **Architecture** (approval gate): modules (Gas Advanced's split is a guide; one module per day-part is fine), the hour split adding up to exactly 40 with the final exam, theory vs practice, where the simulator sessions go, and what builds on which IGF Basic module. Show it to Aleksis and wait.
3. **ILO map** (approval gate): the 29 planned outcomes 1:1 to the topics, mapped to modules, exercises and test questions. Wait for approval.
4. **Exercises first**, then the scripts module by module (approval gate each), then build with the workflow.
5. **Assessment:** two test variants, at least 3 questions per outcome each, the 70 % final with one retake, and the practical marking criteria. Module checks carry no pass mark (L27 / L45); the 70 % is only the final.
6. **Check against the feedback list above** on every module before calling it done, plus the factory's own figure review.

## Rules
- Real photographs first, in slides and trainee tasks. Never an AI image of equipment a trainee must recognise. Keep a list of photos to take at Novikontas (the simulator consoles first).
- **3D render videos (Thauma).** Aleksis can make 3D render videos with Thauma. Where a slide teaches motion or something a camera cannot see, write a detailed video prompt for that slide and put a placeholder on the slide (with the prompt in it) until the video arrives. Examples: a procedure in sequence (cool-down, inerting, bunkering hook-up to disconnection), the inside of a tank or pump, boil-off and pressure build-up, ESD closing valves along a line, gas from a leak spreading.
  - Each prompt says:
    - the learning point;
    - what is in the scene (real equipment, real proportions and arrangement, with source and page);
    - what moves, in what order and with what timing;
    - the camera path;
    - the length (10-40 s);
    - 16:9 at 1920 x 1080 or more;
    - no words baked in (the deck's labels go over it, so they can be translated and corrected);
    - what must NOT appear (wrong arrangement, equipment Novikontas does not have);
    - the poster frame.
  - Collect them all in `course/working_claude/THAUMA_VIDEO_PROMPTS.md`, ordered by module and slide, with the slide's own words beside each.
  - A video never replaces a real photo where the trainee must recognise the real thing: use it for mechanism and sequence, with the photo beside it.
- Every fact has a source and a page. Where sources conflict, write it down.
- Token rules from the global CLAUDE.md: Grep / Glob first, read narrowly. Visual QA in Sonnet subagents. Module builds on Sonnet; design and judgement in the lead.
- **Do NOT:**
  - push, open a PR, or commit to the factory's `main`;
  - publish to the tablets or the training-app repo;
  - edit IGF Basic or the Gas Advanced course;
  - send messages or emails;
  - delete anything;
  - change a Gas Library file except through its tools.
- If you find a factory bug, work around it and record it in the handoff. Do not fix the factory in this session.
- Keep a running handoff, `C:\Users\aleksisv\Desktop\Kursi\Paplašinātais kurss IGF\HANDOFF_IGF_ADVANCED.md`, in plain words:
  1. what exists and in what state;
  2. every decision taken, with its reason;
  3. what waits for Aleksis's approval, and the file to open;
  4. open questions, source conflicts, missing material and photos to take;
  5. factory bugs met;
  6. time and cost used.
  
  Also keep `course/working_claude/COURSE_STATE.md` current, as in IGF Basic.
- If this runs unattended (nobody to answer), build `--draft` only, never approve a gate on Aleksis's behalf, write every decision into the handoff and keep going with whatever can be built.
