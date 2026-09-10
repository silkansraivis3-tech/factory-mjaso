---
name: course-tablet-publisher
description: >
  Publish a finished course onto the NOVIKONTAS tablet platform - the trainee (Training)
  and instructor (Trainer) Android terminals - and into the shared GitHub repository.
  Trigger on: publish this course / publish to the tablet system / add this course to the
  Android training platform / sync with the trainee tablets or the instructor app /
  prepare tablet content / package the finished module or course / add a new NOVIKONTAS
  course / update an existing course in the shared platform / prepare for the
  Trainer/Trainee APK / ready for tablet testing / ready for Test Drive. Also use
  PROACTIVELY when a course-building session has produced trainee tasks, decks, handouts
  or assessments and the next step is getting them onto the tablets. It sorts every file
  into trainee / instructor / shared / internal, refuses to publish if instructor-only
  material, a credential, a developer address or a missing asset would ship, registers
  the course, and publishes on a branch for review. Course-agnostic; GAS BASIC is only
  the reference. NOT a course designer - never rewrites ILOs, content, answers or
  maritime facts (course-factory, novikontas-*), never redesigns screens
  (course-module-ux, course-task-ux).
---

# NOVIKONTAS course tablet publisher

**v1 (2026-09-08) · Maintained by Raivis · Personal — installed for Raivis only, not org-published**

**What this owns:** getting validated course content from an author's folder onto the two
tablet terminals and into the shared repository, safely, while several colleagues do the
same thing for different courses.

**What this must never do:** change what a course teaches. No rewriting ILOs, no inventing
maritime facts, no "improving" an answer key, no redesigning an approved screen. If content
is wrong, say so and stop — do not fix it under the heading of publishing it.

```
authoritative course outputs → identify tablet-relevant → validate → separate roles
    → package/register → test → git branch → pull request → shared default branch
```

---

## 0 · Read this first, then do only what the mode needs

`knowledge/platform.json` **is the authority** on every path, root, pattern and rule. Read
it; do not restate its paths from memory, and do not hard-code a path this file does not
name. When the platform changes, that file changes — not the scripts, and not this file.

| The ask | Do |
|---|---|
| "publish / sync / package this course", "ready for tablets" | the **publish flow** below |
| "add a NEW course to the platform" | `references/course-package.md` first, then the publish flow |
| "will this pass?", "check it without publishing" | the publish flow, dry run only — stop after step 3 |
| "why isn't the platform generic yet?" | `course_identity_surface` in `knowledge/platform.json` |
| how a course must be BUILT (hours, ILOs, decks, screen craft) | **not here.** `course-factory`, `course-module-ux`, `course-task-ux` |

---

## 1 · The publish flow

One command does all of it. It is a **dry run by default** and touches git only when told to.

```bash
python scripts/publish.py --repo <android project> --course-id <slug>
python scripts/publish.py --repo <android project> --course-id <slug> --publish
python scripts/publish.py --repo <android project> --course-id <slug> --publish --merge
```

1. **Identify the course.** The slug is the `courses/<slug>/` folder name and the `id` in its
   `course.json`. If you cannot derive the slug, the title and the version safely, **ask one
   short question** — never guess an identifier that ends up in a branch name and a registry.
2. **Gate it** (`scripts/gates.py`). Eight checks; `FAIL` stops everything before git is
   touched. See §2.
3. **Register it** (`scripts/registry.py`). Regenerates the installed-course list from the
   course packs themselves.
4. **Publish** (`scripts/gitpub.py`): fetch, branch `course/<slug>/<version>`, stage **only
   this course's paths**, show the diff shape, commit, push, print the pull-request URL.
5. **Report** to the human: verdict, what was staged, the PR URL, and every warning that a
   person needs to read. Never claim a merge that did not happen.

Run the scripts. Do not re-implement their checks in conversation, and do not talk a human
through git by hand — the rails in `gitpub.py` are the point (see §4).

## 2 · The gate, and the one rule that matters

`gates.py` classifies every published file as **TRAINEE**, **INSTRUCTOR**, **SHARED** or
**INTERNAL**, then runs: identity · roles · secrets · offline · addresses · junk · assets ·
rights.

**The hard requirement: instructor-only material never ships in the trainee package.** The
platform enforces this structurally — the trainee flavour does not package the instructor
source set at all — so the only way to break it is to put an instructor-only *file* inside
the trainee tree. That is exactly what the roles check looks for, and a new one **FAILS**.

Verdicts: **FAIL** stops publication. **WARN** publishes and prints what to read. `--strict`
turns every warning into a failure — run it before a release to see the true state.

**Accepted debt is real and visible.** `knowledge/known-findings.json` lists findings that
already existed on 2026-09-08 (an answer key and several assessor documents inside the
trainee tree, and the marking engines beside them). Those are downgraded to warnings *and
named in every report*, so the working course can still be published while the debt stays in
sight. Adding an entry there is a human decision, states its fix, and is never a way to
silence something new.

If a gate fails: **report the exact files and stop.** Do not move a file, loosen a pattern or
edit `known-findings.json` to get past it unless a human asks for that specific change.

## 3 · Two layouts, and which to use

- **`courses/<course_id>/` (pack)** — use for **every new course**. Self-contained, so two
  colleagues publishing two courses share no file. `course.json` is its manifest.
- **legacy** — GAS BASIC only. Its files sit at the terminal roots with no course segment in
  any path. It is publishable; **do not create a second course this way**, and do not convert
  it without being asked (it moves hundreds of files and every relative link with them).

`references/course-package.md` has the pack contract, the `course.json` fields, versioning,
and the honest list of what still needs wiring for a truly generic platform.

## 4 · Git, and working alongside colleagues

`references/git-workflow.md` is the detail. What must not be forgotten:

- **The default branch is detected, never assumed.** This repository's is `master`, and
  people will say "main". The scripts ask the remote.
- **Only the course's own paths are ever staged.** The working tree routinely carries
  hundreds of unrelated changes; `git add -A` would publish a colleague's half-finished work.
  `gitpub.py` refuses if anything outside those paths is in the index.
- **Fetch before branching**, and if the base moved, merge it in before pushing.
- **A content conflict is never resolved by guessing.** Stop and say who else published.
- **Never** force-push, never rewrite the default branch, never delete a branch, never commit
  a secret, never commit the report file or scratch files. There is no flag that does these.
- **`--merge` is the only route into the default branch**, and it needs a passing gate and a
  clean merge. Without it a reviewable pull request is left and you say so plainly.

## 5 · Reporting back

Say, in plain sentences: the verdict; what would ship (counts by role); anything a person
must read; the branch and the PR URL; and whether it reached the default branch or is waiting
for review. If you refused, lead with what to fix, by path. Never imply a course is live on
the tablets when only a branch exists — the APK still has to be built and installed.

---

## Deliberately outside this skill

| Concern | Owned by |
|---|---|
| Course build order, accredited hours, ILO immutability, deck↔run↔manifest crosscheck | `course-factory` (its `tablet/` lane and `knowledge/delivery-contract.json`) |
| One-page module architecture, screen measurement, run-script generation | `course-module-ux` |
| Trainee task screens — answering, navigation, completion | `course-task-ux` |
| What a course teaches or assesses; exercise forms, handouts, written tests | the `novikontas-*` family |
| Building or installing the APK | the Android project itself; publishing is not installing |
