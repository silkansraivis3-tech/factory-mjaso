# Course patterns

What finished courses taught the factory — one file per course, `COURSE_PATTERN_<course>.md`. **The
file name `patterns/` next to this folder is taken by the visual engines; this folder is the other
kind of pattern.**

A pattern is **guidance for a later course, never a rule, and never above what that course's operator
asks for** (L32). Each one names the course, its course type, its subject and who made it, so a later
course can judge whether it fits at all.

How one gets here:

1. At the end of a course, when the operator says they are happy, the factory drafts the pattern from
   the course's `FEEDBACK_LOG.md` (`course_memory.py draft-pattern`).
2. The factory **shows it to the operator in plain language**. They may change or remove any point.
3. Only on their approval is it saved, with their name and the date (`course_memory.py approve-pattern`).
4. The owner copies the approved file into this folder, commits and pushes. Every colleague receives it
   with the next plugin update.

A new course lists the approved patterns with `course_memory.py patterns --course-type <type>` and reads
the ones that fit. Drafts and unapproved files are never listed.
