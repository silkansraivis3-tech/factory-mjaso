# Proposal — course review platform inside the admin site

Written 2026-10-28 (Aleksis, from Aigars's idea). **Status: idea and design only — nothing built.**
Where it lives: https://novikontas-admin.vercel.app/#/courses (repo `novikontas-training-app`, `admin/` +
`backend/supabase/`), with the Course Factory doing the rebuilds.

## The idea in one paragraph

A finished course is on the platform. An instructor or reviewer opens it, goes module by module, and
improves it at one of three levels: recommend a change, tell Claude what to change, or edit the slides
themselves. Every change is checked, saved as a new course version and is running on the tablets without
anyone rebuilding or uploading by hand.

## The three levels (Aigars)

| | Level 1 · Recommend | Level 2 · Tell Claude | Level 3 · Edit yourself |
|---|---|---|---|
| The reviewer | writes a note on a module or a slide | writes what should change | edits the slide in an editor |
| What happens | Claude sorts it (facts or design, which slide, how urgent) and prepares a ready fix; it lands in Aleksis's and Raivis's inbox | Claude makes **3 versions** (smallest fix / fuller rewrite / another way of showing it); the reviewer accepts one, declines, or asks again with a note | the edit is saved as a change - no AI |
| Who decides | Aleksis or Raivis - one click: accept the prepared fix, change it, decline | the reviewer | the reviewer - **no second look**, the editor is in charge of the change |
| Goes live | after that click | on accept | on save |
| Speed (estimate, not measured) | a notice in seconds | ~1-3 min for text, ~5-15 min for figures | ~1 min (rebuild + checks) |

## Decisions so far (Aleksis, 2026-10-28)

1. **Permissions per person.** Each person gets switches for what they may do — Recommend, Ask Claude,
   Edit. No fixed "reviewer" role.
2. **Level 3 gets no second look.** The editor's name is on the change in the history; Undo is there.
3. **How Level 1 notices reach us** (email or only an inbox in the admin) — **still open.** Until then:
   the inbox.

## What every change goes through, at every level

All three levels make the same thing — a **change**: a list of exact edits (`s07.title -> "..."`, a
layout, a photo, a figure label). One pipeline handles it:

1. **Automatic hard checks** (not a person — these block the save at any level): official hours unchanged,
   Main ILO wording unchanged, task page file names unchanged (results are filed by path), the factory's
   package check including the classroom's own importer, trainee pages never link instructor files.
2. **A new course version** - the version number goes up, the old one is kept.
3. **Never live mid-class** - if a class is running the course, the publish waits until it ends (the
   tablets pick up a new version within ~50 min, and slide state is keyed by slide number).
4. **Undo** - republishes the previous version.
5. **History and learning** - who, what, why, which of the 3 versions was chosen; written to the
   course's FEEDBACK_LOG so the factory learns what reviewers prefer.

## Level 3 — the editor

Never raw HTML: the slides are compiled from the approved script, and a hand-edited page would fail the
word match and be lost on the next build. The built slides already carry `data-script-field` markers
(used by `check_script_match.py`), so a tap on a sentence finds its line in the script. The editor offers:

- **Text** — edit any line in place
- **Layout** — choose from the shared layouts (the build sheet; it never undoes approval)
- **Picture** — swap for another photo from the course's photo catalogue
- **Figure** — labels and steps in the figure's spec
- **Order** — move or hide slides (task page names stay)

The preview changes in the browser at once; the real rebuild and checks run on the worker before it goes
live.

## What exists already (read from the code, 2026-10-28)

**Admin and backend** (`novikontas-training-app`):
- Plain JavaScript admin (`admin/app.js`), hash routes `#/courses`, `#/courses/<id>`; hosted on Vercel;
  server work in Supabase Edge Functions (`classroom`, `course-import`, ...). No LLM is called yet.
- Login with Google, `@novikontas.org` allowlist, roles owner / editor / viewer / instructor
  (`backend/supabase` migrations 007, 008).
- Versions: `course_releases` - fixed once made, one published per course; publishing a new one demotes
  the old (`009_atomic_course_import.sql`). `courses.status` already allows `'review'`, unused.
- Tablets load the published release from storage through the hosted classroom (`classroom` function
  `assets`, the service worker `admin/classroom/sw.js`), refreshed every ~50 min.
- Limits: 6000 files, 300 MB, 15 MB a file; the import function takes 12 MB a request.
- The two deploy notes disagree (DEPLOYING.md: Vercel deploys on push to main; CLAUDE_CODE_CONTEXT.md:
  run `vercel --prod` by hand) - check before building.

**Factory:**
- The fix lane already does Level 2's core: an LLM turns a sentence into `changes.json`; `fix.py propose`
  / `apply --confirmed` / `rebuild` / `approve --by` are plain Python (`plugin/skills/course-factory/fix/`).
  `propose` records a `base_hash`, so two reviews of the same module can't overwrite each other.
- Phase A compiles a module in 17-38 s with no agent; the fix sweep ~4 s a module.
- What may change without new approval vs locked content: `retrofit/knowledge/content-lock.json`.
- Needs Python, Node and headless Chrome; no GPU.

## What is missing

1. **The course source on the platform.** The admin holds only the finished HTML; the factory needs the
   script, build sheet, figure specs and photos. Proposal: a **private Git repository per course** - a
   version is a branch, accept is a merge, a release is a tag (history and diffs for free).
2. **A worker** where Claude and the factory run. Start: a PC or virtual machine running Claude Code
   headless with the course-factory plugin (the factory is tested on Windows). Later, if a Linux trial
   passes: Claude Managed Agents (Anthropic runs it; hard cost cap per job; the repo attached from
   GitHub). API and service keys stay on the worker / in Supabase secrets, never in the browser.
3. **The review screens** in the admin: the module with comments, the inbox (Level 1), three versions
   side by side with what changed in plain words and before/after pictures (Level 2), the editor
   (Level 3). Previews reuse the classroom loader (`/classroom/pack/<id>/`).
4. **Supabase:** tables `course_reviews`, `review_comments`, `review_variants`, `review_jobs`, the
   per-person permission switches; a `review` Edge Function.

## Build order

0. **Trial:** on a copy of an IGF module, one written review -> 3 versions with the fix lane, timed. Decides
   the worker.
1. **Level 1** - review screen, comments, inbox, Claude's sorting and prepared fix. Useful from day one.
2. **Level 2** - worker, 3 versions, previews, accept -> publish, wait for class to end, Undo.
3. **Level 3** - the editor, reusing everything above.
4. Then: reviewing all modules at once; the chosen versions become the factory's answer key.

## Risks

- **Review text goes to an agent that can write files** - the agent may touch only that course's folder,
  no network but Supabase, a cost cap per job.
- **Mid-class changes** - handled by waiting for the class to end.
- **Old tablet browser (Chrome 83) and the tablets' block on other sites** - versions must pass the same
  package checks; reviewing itself is in a normal desktop browser.
- **The training app is Raivis's repo** - built on a branch, PR for Raivis to review.

## Still to decide (Raivis, Aigars)

- Email for Level 1 notices, or only the admin inbox.
- Where the worker runs: office PC, virtual machine, or Managed Agents.
- Course source: Git repositories (proposed) or a storage bucket.
- External reviewers: the allowlist takes only `@novikontas.org` today.
- A cost cap per Level 2 job (unmeasured; likely a few euros for three versions).
