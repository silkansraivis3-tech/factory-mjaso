# PREVIEW, APPROVAL, PUBLISH — the three states a course is in

**v1 (2026-09-14)**

A course is always in exactly one of three states. Knowing which one answers every question
about what may be touched.

| State | Where the course lives | What may be written | Who ends it |
|---|---|---|---|
| **PREVIEW** | the colleague's own course folder | the course folder only | nobody — it is the default |
| **APPROVAL** | same | nothing | a person, in a sentence |
| **PUBLISH** | same, plus the Android project | the course's own paths in the Android project | the gate, then git |

**PREVIEW is the default.** A course is in PREVIEW from the moment it exists. It does not
have to be put there and cannot fall out of it by accident.

---

## 1 · PREVIEW

The working course stays **completely outside** the Android repository. No Android Studio,
no tablet, no terminal, no git.

```bash
python scripts/preview.py --course <course folder> --open
```

That writes `REVIEW.html` beside the course and opens it in the normal default browser. The
page lists every surface the course actually has — the deck, the tasks, the handout, the
practical cards, the assessment, the instructor plan — and links each one. It also carries
the checklist of what to look at before approving.

**Why a generated page and not just "open module.html".** A colleague reviewing a course has
to find the tasks, the handout and the assessment, and those live in folders whose names
they have no reason to know. And `REVIEW.html` deliberately carries **no course CSS**: a
review surface that depends on the thing under review tells you nothing on the day that
thing is broken.

### file:// is enough — measured, not assumed

The obvious worry is that a browser will refuse to run a course opened as a file. It was
tested end to end: the real course, a real `file://` origin, the real default browser.

| | |
|---|---|
| external CSS · external JS · SVG | **LOADED** |
| `localStorage` · `sessionStorage` | **OK** |
| deck engine · 6/6 figures · 44 slides | **built** |
| console errors | **0** |
| `fetch()` of a local file | **BLOCKED** |

Only `fetch` is blocked, and Course Factory output uses no `fetch`, no `XMLHttpRequest` and
no ES modules. So the colleague double-clicks a file. **No server, no port, no terminal, no
localhost to understand.**

That is a property of the output, not a law of nature, so it is enforced:
`gates.py` check **`runtime`** fails a course that adds any of the three. The day someone
reaches for `fetch`, the gate says so — rather than the preview breaking silently and the
failure looking like a broken course.

One honest caveat: every `file://` page shares one origin, so `localStorage` is shared
between previews of different courses. Harmless for review; it is why PREVIEW is a review
surface and the tablet is the delivery target.

---

## 2 · APPROVAL

> **Without explicit human approval, the Android project is READ ONLY.**

Approval is a sentence from a person, about a named course. In their own words:

- *"Approved. Publish this course."*
- *"Publish this approved course to the NOVIKONTAS training app."*
- *"Send this course to the Android app."*

**These are not approval, and must never be treated as it:**

| Said | Means |
|---|---|
| "make this module better" | course work. PREVIEW. |
| "fix the tasks" / "redesign module 1" | course work. PREVIEW. |
| "is it ready?" / "will it pass?" | run the gate, dry run. Report. Do not publish. |
| "publish it" said of a course nobody has reviewed | ask them to review it first. |
| approval given earlier, for a previous version | not approval for this one. |

Approval is **per course and per version**. A course re-published after changes needs the
person to say so again — the version in `course.json` is what they approved.

### How it is enforced

`publish.py --publish` refuses without `--approved-by "<name>"`, **before the platform file
is opened**, so a mistyped publish cannot read, write or touch the Android project at all.
The name is written into the commit as an `Approved-by:` trailer, so the repository records
who approved a course rather than only who ran a script.

This is a gate against the **accident** — the wrong flag, an over-eager agent, a command
recalled from shell history. It is not a password and it is not security. The approval that
matters is the human sentence; this is where that sentence gets written down.

---

## 3 · PUBLISH

Only after approval:

```bash
python scripts/publish.py --repo <android project> --course-id <slug> \
       --publish --approved-by "<name>"
```

```
gate  →  registry  →  link check  →  branch  →  commit  →  push  →  pull request
```

Every step refuses rather than guesses. `gates.py` runs first and a **FAIL stops everything
before git is touched**. Only the course's own paths are ever staged. The default branch is
detected from the remote, never assumed.

**Publishing is not installing.** A push puts the course in the repository. The owner still
pulls, builds the APK and installs it on the tablets. Never tell a colleague their course is
"on the tablets" when a branch exists.

---

## 4 · What the colleague never has to do

Android Studio · own a tablet · open a terminal · know git · know Kotlin · understand
localhost, ports or servers · edit application code to add a course.

If any of those becomes necessary to add a normal course, that is a defect in this
platform, not a step for the colleague to learn.
