# Law history

Who asked for a law, when, in their words, and which release built it. A record only: nothing here is a rule, and no
skill loads this file. The rule itself is in `plugin/skills/course-factory/SKILL.md` (the table) and `FACTORY_LAWS.md`.

---

**L2** - The factory never re-words a Main ILO. A Sub-ILO's wording is changed only through the expert-reviewed elevation
of L69 (2.142.0, owner, 2026-11-24); before that, `PROVISIONAL` re-expression with an explicit proposal, and L71 and L70
said "the factory never proposes a re-worded outcome". A review started before 2.142.0 finishes by the rules it was
started with.

**L26** - Design part revised 2026-10-15, 2.30.0. Owner: *"claude should tell person about this risk, but still after
person reviews and tells that he wants his way, plugin listens to that."* The same block sat near the top of every
skill until the other skills pointed here instead (`course-factory`, `SKILL.md`).

**L46** - Owner, 2026-10-07: not on every slide, never at a lower quality, only where it makes sense. 2.22.0 built it.
2.118.0 removed the share and the cap: 3D only where the figure's why is spatial (L60, L67 say the same).

**L47** - Owner, 2026-10-14: about EUR 0.10 a picture. 2.73.2 made it one yes per course at Stage 2 with the count and
the euros (`intake.json` `picture_budget`). `nano-banana` 1.2.0 holds `approved_by_user` and the usage log.

**L60** - 2.118.0: 3D only where a slide's why is spatial; `declined_3d` is an optional note. A slide with
`"photo_wanted": "<who asked, why>"` (build sheet, script screen, or the script's top-level `"photo_wanted"`) is never
turned 3D (Aleksis, 2026-10-22, after IGF M02 s07 became a scene on the slide where the instructors asked for a
photo; 2.63.2). Built 2.49.7.

**L61** - Owner, 2026-10-20: *"Implement the layout templates. All slides for all modules that will be made need to be in
this style, it's a RULE. Configure the compiler so it does this style - of course the logo should be our official one,
and the colours from the brandbook."* Built 2.52.0. 2.118.0: words are never cut, moved or paged by the factory; a slide
may have no picture when its words read on their own.

**L62** - The owner, 2026-10-21, after the gas course's Module 1 came out with 29 of 33 slides in one layout: *"Check
module 1 - it is now done with the new templates, see how bad it is. Optimise the factory so the logo looks bigger and
better, and images are upscaled, not this pixel stuff. Also make sure that two types of slides never repeat in a row -
now 6-7 slides are exactly the same layout, and it hurts the eyes."* Same day, on the logo: *"bigger logo, and on blue
slides the logo should be white without background"*; the artwork went from about 8 to about 10.5 vmin tall. 80 / 20 (the
owner, 2026-10-21, after the IGF instructors' review: *"A lot of dark slides"*; Raivis: 80 / 20 for the background
colour, so 80 % light slides). Built 2.53.0 on main, 2.62.0 on the branch that built the same days (the owner's number
was taken by the 2.53.0-2.61.0 line). 2.118.0 turned the look-repeat rule, the dark share and the 80 % light ground into
notes: the compiler never changes a slide's layout to avoid a repeat. Originally "never the same look twice in a row".

**L63** - Aleksis, 2026-10-20, approving a plain-vs-realistic mock-up of the figure kit: *"yes we like this new kit
styling"*, then *"also do the Parts added from courses"* and *"make the ship look realistic aswell, look at real images
of it"*. Built 2.56.0 (as 2.52.0 / L61 on its own branch, renumbered at the merge with the owner's L61, and L62 -> L63 at
the merge with the owner's L62). Printed after L62 from the 2.143 clean-up on.

**L67** - The owner, 2026-11-03, reviewing the template gallery (*"svg SUCKS"*). Built 2.88.0; the compiler writes the
upgraded bodies (`compile/GUIDE.md` 2h), 2.89.0. 2.118.0 removed the 60-80 % 3D share and "never a flat line drawing";
a 3D model of a flat idea is a must-fix (`v_3d_flat`).

**Law count** - Seventy-one laws by 2.106.0; L72-L76 were added in the course-factory table afterwards. The first copy of this record (`plugin/CLAUDE.md`, then `docs/`) was moved in Phase 3 because Claude Code
does not load a plugin-root `CLAUDE.md` and `claude plugin validate --strict` fails on one (finding F-1, confirmed by
the official validator on 2026-09-10).
