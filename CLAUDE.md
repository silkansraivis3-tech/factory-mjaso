# NOVIKONTAS course factory

The `course-factory` and `nano-banana` Claude Code plugins that build accredited maritime training courses for the
NOVIKONTAS tablets. Before changing anything, read the **Current** line at the top of `_claude/CONTEXT.md` and the newest
rows of its version table (the last rows, just above `## Install, and where it lands`) - not the whole file: it is the
history of every release, so grep it for a term when you need its past. `00_READ_ME_FIRST.md` is the short version, and
the laws are in `docs/FACTORY_LAWS.md`.

## A factory request

An issue labelled `factory-request` was opened from the training app's editor mode: the course office saw something in
a built course that the factory itself should do differently. The issue says what, and where it was seen.

- Fix the factory - the skill, script, template or rule that made it - not one course. Courses are not in this
  repository.
- Change as little as the request needs. Follow the code around you: its naming, its comment density, its idiom.
- Run the tests of what you change (`python <test>.py` beside the script, `node --test` for `.mjs`), and add a check
  that would have caught this.
- Record the release: `plugin/.claude-plugin/plugin.json` (patch version for a fix, minor for something new), the
  header of `00_READ_ME_FIRST.md`, the current line and a new row in `_claude/CONTEXT.md`, and the owning skill's
  `MANIFEST.md`.
- Open a pull request that says what changed and how it was checked. Never merge it: the owner reviews every change.
- If the request is unclear, or would break a law in `docs/FACTORY_LAWS.md`, say so on the issue instead of guessing.

## Writing

English only: new words the factory writes (task-page and answer-key words, page labels, engine words) go in English;
add no Latvian or Russian translations - a language table without a word falls back to English.

Plain words, no source or authorship notes in code comments (no "owner, <date>", no version stamps beside code): the
version records hold the history. Learning outcomes and course facts are never changed by the factory's code.
