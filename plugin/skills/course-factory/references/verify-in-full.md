# Verify before reporting done, in full

*Moved here word for word from `course-factory/SKILL.md` in 2.11.0 (Phase 5, step 11) so the
skill file every session reads stays light. Nothing was deleted or reworded. SKILL.md keeps the list of checks; this is why each one exists. Read it at sign-off.*

---

## Verify before reporting done

Run these, read the output, then report. A green exit is not proof the work happened — inspect
the line for the thing you changed.

1. `hours/scripts/check_hours.py` — minutes match the programme
2. `coverage/scripts/check_syllabus_coverage.py` — every **itemised outcome** of the model course
   is taught. Not the same question as the topic record, and it found the only real content gap in
   266 outcomes on a course whose topic record was already green.
3. `tablet/scripts/verify_course.py` — structure, counts, check→hand-off order
4. `tablet/scripts/verify_links.py` — every link resolves in the **merged** asset root
5. `tablet/scripts/audit_navigation.py` — every page is **reachable** and has a way back. Not the
   same question as (4): a section whose own index nothing links is invisible in the built app
   however good its links are. That was 28 pages on GAS BASIC — every safety brief, rotation plan
   and practical write-up — with `verify_links.py` green.
6. `tablet/scripts/crosscheck_tasks.py` — deck ↔ run script ↔ tablet manifest agree
7. `course-module-ux`'s measurement lane for the screens themselves
8. `course-visuals/scripts/check_visuals.py` and `check_assets.py` — the deterministic visual
   checks and the provenance record. Then, in the page, `GBVerifyFigures.run()` and
   `await GBVerifyFigures.motion()` — every figure rendered, and every figure alive rather
   than a picture (L20). Then `course-visuals/review/GUIDE.md`, which asks the question
   no script can: **does this visual actually teach?** Nothing at `RIGHTS_REVIEW_REQUIRED` may ship.
9. `course-visuals/scripts/check_visual_first.py <module> --strict` — L23. Every topic screen
   leads with a figure, or says in writing why it has none. Then
   `course-visuals/scripts/write_visual_handoff.py <module>`, which should print "nothing to hand
   off"; if it does not, the module is finished as far as it goes and the handoff leaves with it.
10. `course-module-ui/scripts/audit_ui.py --strict` over a **new** module's stylesheets — the
   visual sign-off. `--strict` is right for new work and wrong for shipped material: never point
   it at a delivered GAS BASIC or Electrical Technician module. Those carry known drift that
   `course-module-ui` records by name; **report drift, do not repaint a signed-off deck.** The
   point is that new work does not start a second visual dialect.

(2) and (5) exist because (1), (3), (4) and (6) all passed on a course that was missing an
accredited outcome and shipping a dead section. **Every check here was added after something got
through the others.**

11. `scripts/check_slide_text.py <course>` — **what the pages SAY**. Internal shorthand,
    version control on a title slide, and an IMO model course cited as a source or credited
    for a figure. A model course governs what a course must COVER; it is not a source of
    fact, and a slide that cites one tells the room a syllabus is where the fact came from.
    The factory's own markers are caught here too — they belong in `factory-notes.md`.
    Instructor plans may cite a model course and are reported, never failed (L22).

12. `scripts/check_plain_language.py <course>` — **L25, and it is the last one for a reason.**
    Everything above checks the course; this checks the report you are about to hand over. The
    person reading it does not work in IT: no bare jargon, no path they cannot find, and no
    problem named without a way out. Read your own report against it before sending it.

13. `retrofit/scripts/detect_expert_edits.py <module> --record --version <v>` — **last of all,
    after everything else passes.** It records a fingerprint of every file this run produced, so
    the next retrofit can tell the expert's later changes from the factory's own work (L24). A
    record written before verification records work that may still be rolled back.

14. **In retrofit only** — `retrofit/scripts/check_language.py <course> --declare <LANG>` (the
    course did not change language), and `retrofit/scripts/classify_module.py` **again**. A
    retrofit that started at C and still classifies C has not finished.

Then write `templates/factory-notes.md` into the course folder: what was produced, every marker
with its source, the achieved ratio, what was moved to the handout and why, and a final section
of **feedback on this skill**. That last section is the only channel through which real use
reaches the skill — it is written by this skill during the run, never left for a human.
