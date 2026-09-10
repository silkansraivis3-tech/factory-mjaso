# The course package — what a course must give the tablet platform

**v1 (2026-09-08)**

Read this when adding a **new** course, or when asked why the platform is not yet generic.
`../knowledge/platform.json` is the authority on paths; this file explains the shape and the
decisions.

---

## 1 · One folder per course

```
app/src/main/assets/training_terminal/courses/<course_id>/     TRAINEE
    course.json               the manifest - id, title, version, modules, status
    module_NN/tasks/          the task pages that module's screens announce
    module_NN/assets/         that module's figures and photos + _photo_meta.json
    module_NN/documents/      reference cards a trainee keeps            (optional)
    module_NN/simulator/      simulator briefs                            (optional)
    handout/index.html        the take-home
    assessment/               the final assessment, separate from module checks

app/src/instructor/assets/instructor_terminal/courses/<course_id>/   INSTRUCTOR
    plans/                    one module plan per module
    prepare/                  pre-class setup where a facility must be booked
    record/                   the practical skills record
    answers/                  answer keys, marking criteria, case analyses
```

`<course_id>` is a lowercase slug: `gas-advanced`, `fire-fighting`, `first-aid`. It is the
folder name, the `id` in `course.json`, the branch name and the registry key. Pick it once;
changing it later is a rename across every path.

**Why one folder per course.** Two colleagues publishing two courses then touch no file in
common, so they cannot conflict. It is also what `course-factory`'s own delivery contract
already specifies, so this is not a new invention.

**Shared engines are referenced, never copied.** `gb_*.js` / `gb_*.css` live once at the
terminal root. A copy inside a course goes stale the first time the engine is fixed — that
has already happened on this platform, where one completion engine exists in five identical
copies.

---

## 2 · Roles: four buckets, and the one that must stay empty

| Role | Where it lives | Reaches a trainee tablet? |
|---|---|---|
| **TRAINEE** | the trainee course pack | yes |
| **INSTRUCTOR** | the instructor course pack | no — the trainee flavour never packages it |
| **SHARED** | engines at the terminal root | yes, by reference |
| **INTERNAL** | authoring folders, working areas, generators, `.bak` | never published |

**Instructor-only means:** answer keys, model answers, marking criteria, run sheets, module
plans, observation checklists, assessor records and signature blocks, case analyses, the
deck's answer payload (`gb_answers.js`), the answer-reveal engine, and any marking engine
that carries the criteria.

A trainee page may legitimately state *its own* standard — "six of eight to pass" — and the
gate allows that. What it must not carry is the marking apparatus.

**A button is not a gate.** Two module checks on this platform reveal an instructor view by a
plain click with no authentication. If a page has two audiences, split the file; do not hide
one behind a class name.

---

## 3 · `course.json`

`../templates/course.json` is the starting point. Fields:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | must equal the folder name |
| `title` | yes | as the course is called on the certificate |
| `version` | yes | `MAJOR.MINOR.PATCH` |
| `status` | yes | `draft` while it is being built, `released` once a class has been taught from it |
| `modules` | yes | how many modules the pack contains |
| `programme` | recommended | the accredited programme document this course implements |
| `academic_hour_min` | recommended | 40 on this programme; hours belong to `course-factory` |
| `published` | written by you | append `{version, date, branch}` on each publication |
| `allow_overwrite` | rarely | only to republish a `released` version deliberately |

---

## 4 · Versioning

Never silently overwrite a released version.

| Situation | Do |
|---|---|
| **new course** | `1.0.0`, `status: draft` |
| **still unreleased** | keep the version, publish again over the same branch |
| **content change after release** | bump MINOR (`1.1.0`) — a new branch, a new PR |
| **fix to a released version** | bump PATCH (`1.0.1`) |
| **restructured course, new programme** | bump MAJOR |

The branch is `course/<slug>/<version>`, so each version has its own reviewable history. The
publication record lives in the course's own `course.json`, which nobody else edits.

---

## 5 · Registration

`scripts/registry.py` regenerates
`training_terminal/courses/registry.js` (`window.GB_COURSES`) by scanning every
`courses/*/course.json`. It is generated, sorted and deterministic: on a merge conflict, take
either side and re-run the generator. Never hand-merge it.

The format is a JS global because that is how every other registry on this platform loads
(`GB_TASKS`, `IT_MODULES`, `IT_RUN`). A runtime `fetch` of JSON would be a second mechanism
in an offline WebView.

---

## 6 · What still blocks a truly generic 20-course platform

**Update 2026-09-09.** The shells now read their course from data: `gb_config.js` names it once (`COURSE`, `COURSE_ID`), the generated `courses/registry.js` lists what the APK holds, the instructor's course chooser derives its installed list from that registry, and every title in the two shells comes from `GB_CONFIG`. The live-class server lists its courses in `server/courses.json`. Points 1 and 3 below are done; 2 and 4 remain and are what a second pack still needs.

**Update 2026-09-09 (evening) — the manifest loader.** `training_terminal/gb_courses.js` now
loads a course's manifests from wherever the registry entry says they are: the entry's
`trainee` prefix for `gb_tasks.js`, its `instructor` prefix for `it_run.js`, `it_content.js`,
`it_record.js`. GAS BASIC's prefixes are empty (its files sit at the terminal roots, point 4);
a packed course sets `trainee: "courses/<id>/"` and `instructor: "courses/<id>/"` and puts
its manifests there. Every page that used to hard-code `<script src="gb_tasks.js">` now
carries `<script src="gb_courses.js" data-load="gb_tasks.js">` (instructor pages add
`data-root="instructor"`), preceded by `gb_config.js` and `courses/registry.js`. The loader
is synchronous (`document.write`) on purpose — the manifests must exist before the shell's
own script runs, and an offline WebView has no reason to fetch. `gb_sync.core()` strips
`courses/<id>/` before deriving a page's kind and unlock scope, so the sync regexes work
inside a pack. What is still per-course at the root: the module lists in `live.js`, the record
page and `handout.js` (point 2). A second pack therefore needs: `course.json` + registry entry
with the two prefixes, its manifests under the prefix, and its pages under `courses/<id>/`.


**Say this out loud rather than hiding it.** Publishing works today; the two terminals do not
yet *discover* courses. `course_identity_surface` in `knowledge/platform.json` has the full
list. The substance:

1. **Nothing reads the registry yet.** Course identity is in code: `gb_config.js`
   (`COURSE`, `RUN_CODE`), a duplicated `COURSE_TITLE` in both terminals, `it_auth.js`'s
   `INSTALLED` array, and a regex in `gb_tablet.js` that strips the course name out of a page
   title. A new course needs those touched by hand.
2. **The module list exists six times** (`GB_TASKS`, `IT_MODULES`, `IT_RECORD`, `live.js`'s
   `MODULES`, a printable record page, and `handout.js`) and the six already disagree — the
   handout list has seven modules and a glossary where the others have eight.
3. **Two structural collisions.** `gb_sync.js` derives its unlock scope with
   `/^modules\/(m\d)\//`: single-digit, and *two* courses would both produce scope `m1`, so
   their unlocks would collide in the backend. And `RUN_CODE` `GAS101` is also a task code —
   one string meaning two things.
4. **GAS BASIC is not in a pack.** Its files are at the terminal roots, so a second course
   cannot reuse those locations.

**The smallest honest next step**, when someone asks for it: make the terminals read
`registry.js` and `courses/<id>/course.json` instead of their in-code constants, and put the
course id into the sync scope. That is a contained change to a handful of files — but it
touches the code that runs a live class, so it needs its own session, its own testing on the
tablet, and the owner's go-ahead. It is not part of publishing a course.

---

## 7 · Stage A now, Stage B later

Today a course ships **inside the APK** (Stage A): publish to git, build the APK, install.
The design intent is that the app becomes a generic runtime and courses become **versioned
downloadable packs** (Stage B).

The boundary is already drawn where it needs to be: a course is a self-contained folder plus
one registry entry, and `course.json` already carries the id, version and status a download
manifest needs. Moving to Stage B changes the *publishing target* — from asset folders to a
pack artefact — and changes **nothing** about how a course author works or how this skill
gates a course. When that day comes, `knowledge/platform.json` gains a target section and
`gitpub.py` is untouched.

One thing not to do meanwhile: make the tablets fetch course content at class time. A
classroom may have no network, and the terminals are deliberately offline-capable.
