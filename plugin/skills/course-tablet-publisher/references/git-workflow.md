# Git — how a validated course reaches the shared branch

**v1 (2026-09-08)**

`scripts/gitpub.py` implements all of this. Read this file to know *why* it refuses things;
do not perform these steps by hand, because every rail below is a property of the arguments,
and a script can refuse where prose cannot.

---

## The shape of it

```
fetch → branch course/<slug>/<version> off the base
      → stage ONLY this course's paths → show the diff shape → commit
      → push → pull-request URL
      → (only with --merge, and only on a passing gate) merge into the default branch
```

---

## Five rails, and the accident each one prevents

**1 · The default branch is detected, never assumed.**
This repository's default branch is **`master`**. Colleagues and prompts say "main". A skill
that hard-coded either name would branch off nothing, or off the wrong thing. `gitpub.py`
asks the remote (`ls-remote --symref origin HEAD`) and falls back sensibly.

**2 · Only the course's own paths are ever staged.**
The working tree here routinely holds **hundreds** of unrelated changed files — at the time
this skill was written, 266. `git add -A` would sweep somebody's half-finished module into a
course publication. So staging is `git add -- <pathspec>...`, and afterwards the staged set
is *verified* against those pathspecs. If anything else is in the index the publish is
refused, naming the files, and the fix is `git restore --staged <those paths>` (which keeps
the working-tree changes) or publishing from a clean clone.

**3 · The gate report is required, and a FAIL is final.**
`commit`, `push` and `merge` all demand `--gate-report`. `FAIL` refuses. `WARN` proceeds and
prints the warning count — see §"Why WARN publishes" below.

**4 · There is no destructive flag.**
Force push, `--force-with-lease`, history rewriting, branch deletion and pushing the default
branch directly are **not implemented**. There is no argument that reaches them. If a
situation seems to need one, it needs a human instead.

**5 · A conflict is never guessed at.**
Before merging, a conflict is detected with `git merge-tree`. On a conflict the publish stops
and reports it. Resolving a content conflict by picking a side is how a colleague's course
gets silently deleted.

---

## Why WARN publishes

This platform has real history: instructor-only documents inside the trainee tree, and a web
font with no bundled copy on about 105 pages. A rail that demanded a spotless PASS would mean
the working course could never be published at all, and the predictable human response would
be to bypass the tool. So `FAIL` stops publication, `WARN` publishes and prints what a person
must read, and `knowledge/known-findings.json` keeps the accepted debt named in **every**
report. `gates.py --strict` shows the true, unforgiving state.

---

## Several colleagues at once

Person A on Fire Fighting, B on First Aid, C on GAS ADVANCED, all publishing the same week.

- **Each course owns its paths.** In the pack layout a publication writes only
  `courses/<id>/` in the two terminals. Different courses share no file.
- **The one shared file is generated, not edited.** `courses/registry.js` is derived from the
  `course.json` files. Two colleagues who both regenerate it produce identical bytes. If git
  still reports a conflict there, take either side and run `scripts/registry.py --write`
  again — never hand-merge it.
- **Fetch first, every time.** `gitpub.py branch` fetches and, if the base has moved, prints
  how far behind you are and how to merge it in.
- **Someone else published the same course.** If a branch for that course and version already
  exists on the remote, that is a real question for a person, not something to overwrite. Bump
  the version, or find out what they published.
- **Never overwrite a colleague's folder** because the local copy looks older. It is not.

---

## The pull request

`gh` is **not installed** on this machine and there is no GitHub token in the environment, so
a PR cannot be opened by API. After pushing, `gitpub.py` prints the compare URL:

```
https://github.com/<owner>/<repo>/compare/<base>...<branch>?expand=1
```

Give that URL to the human. If `gh` is installed later, only this last step gets automated;
nothing else about the flow changes.

---

## Reaching the default branch automatically

`--merge` merges the published branch into the default branch and pushes it. It requires:

- an explicit `--merge` in the task (this is the authorisation),
- a gate verdict of PASS or WARN,
- no conflict against the fetched base.

Without `--merge`, a clean reviewable pull request is left and you **say so plainly** rather
than implying the course is live. There is no branch protection on this repository today and
no CI, which means **the local gate is the only gate** — a good reason to prefer the pull
request unless the task explicitly asks for the merge.

---

## Hygiene the contract already demands

- **Stage every new file.** An untracked asset ships as a missing file, and the failure shows
  up on a tablet, not in the build.
- **Check the shape of your own diff.** `gitpub.py` compares changed lines with and without
  `--ignore-all-space` and warns when most of a diff is whitespace — that means something
  reformatted files it was not asked to touch.
- **Never commit** the gate report, scratch files, `.bak` files, build output, or anything
  under a working area. The gate fails on `.bak` inside an asset tree because those get
  packaged into the APK.
- **Publishing is not installing.** Reaching the branch is not reaching a classroom: the APK
  still has to be built and put on the tablets.
