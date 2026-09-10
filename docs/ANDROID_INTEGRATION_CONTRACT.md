# Android integration contract

**What a generated course must satisfy to work inside the NOVIKONTAS training app.**

Phase 1 · established 2026-09-10 by reading the Android project directly, not from its documentation.

Primary evidence:
`app/build.gradle.kts` · `app/src/main/java/org/novikontas/training/MainActivity.kt` (601 lines) ·
`app/src/main/assets/training_terminal/**` · `app/src/instructor/assets/instructor_terminal/**`

Repository: `github.com/silkansraivis3-tech/novikontas-training-app` — default branch **`master`**
(detected, not assumed; people say "main").

> **This document describes the app as it is. It does not propose changing it.**
> Everything below is a constraint the Course Factory must generate *within*.

---

## 1 · Two apps, one codebase, four flavours

`flavorDimensions += "terminal"`. Each flavour compiles two `BuildConfig` strings that decide
everything else.

| Flavour | applicationId | `START_PATH` | `ALLOWED_ROOTS` | Packages |
|---|---|---|---|---|
| `trainee` | `org.novikontas.training` | `training_terminal/index.html` | `training_terminal/` | `app/src/main/assets` |
| `instructor` | `…training.instructor` | `instructor_terminal/index.html` | `instructor_terminal/,training_terminal/` | `main` + `app/src/instructor/assets` |
| `traineeLocal` | `…training.local` | `training_terminal/local_live/index.html` | `training_terminal/` | test only |
| `instructorLocal` | `…training.instructor.local` | `instructor_terminal/local_live/index.html` | both | test only |

**The role separation is structural, and that is the whole reason it holds.** The trainee APK does
not contain `src/instructor/assets` at all. Answer keys, marking criteria, module plans and the
practical skills record cannot reach a trainee tablet by accident. The only way to break it is to put
an instructor-only *file* inside the trainee tree by hand.

**Gradle merges the flavour source sets into one asset root at build time.** At runtime the two
terminals are siblings. A cross-terminal link is written relative to that merged root and looks dead
in the split source tree — which is why link verification must run against a merged view, and why a
correct link can look broken.

Example, from `instructor_terminal/prepare/m05/practicals/`: `../../../../training_terminal/…`

`compileSdk 37`, `targetSdk 36`, `minSdk 24`. `targetSdk` is deliberately **not** 37: the comment in
`build.gradle.kts` records that API 37 makes the runtime apply hidden-API restrictions to WebView's
own code, the renderer never starts, and pages hang at 10 %. Do not "fix" this.

---

## 2 · How a page is served

There is **no** `WebViewAssetLoader`. `MainActivity` implements the origin by hand.

```
https://appassets.androidplatform.net/assets/<allowed root>/<path>
```

- `ASSET_SCHEME` is `https` for the production flavours and `http` for the LOCAL LIVE test flavours
  (an https top frame silently auto-upgrades http images the classroom laptop cannot answer).
- `assetPathFor()` rejects the request unless the path starts with `/assets/`, then starts with one of
  `ALLOWED_ROOTS`, **and contains no `.` or `..` path segment**.
- Files are read whole into a byte array and served with `Cache-Control: no-store`, and
  `WebSettings.LOAD_NO_CACHE` is set. **Nothing is cached; every navigation re-reads the APK.**
  Page weight is paid on every visit, not once.

### MIME types are a fixed allowlist

`html htm css js mjs json map txt csv svg png jpg jpeg gif webp ico bmp woff woff2 ttf otf eot mp4
webm mp3 wav pdf`

Everything else is served `application/octet-stream`. **`.avif`, `.webmanifest`, `.m4v`, `.ogg` and
`.jsonld` are not in the map.** Use only extensions from that list.

---

## 3 · The seven hard constraints

Enforced by the app. Breaking any one produces a course that looks correct in a desktop browser and
is broken on the tablet.

### 3.1 Only HTML may be navigated to

`shouldOverrideUrlLoading` calls `openPage()`, which returns `false` for anything that is not
`.html`/`.htm`. The navigation is then **blocked** and logged `BLOCKED NAVIGATION`.

> **No links to PDFs. No download links. No `blob:` or `data:` document navigation.**
> Nothing in a course may require a trainee to open a non-HTML document.

`onCreateWindow` is not implemented and multiple windows are not enabled, so **`target="_blank"` and
`window.open()` do nothing** — a deck's "launch the task in a new tab" pattern fails silently.
`onShowFileChooser` is not implemented, so **`<input type="file">` does nothing.**

### 3.2 The only reachable network host is the classroom backend

`shouldInterceptRequest` hands a request to the WebView's own stack **only** for `*.supabase.co` /
`*.supabase.in` over https (plus private LAN addresses, in the two TEST flavours only). Every other
http/https request gets **403 Forbidden with an empty body**.

> **Consequence, and it is a live defect today.** The shipped course loads Raleway from
> `fonts.googleapis.com` on roughly 105 pages. On the tablet that request is answered 403 by the app
> itself: the brand typeface **never loads on the tablet at all**, and every page issues two blocked
> requests. `course-factory/knowledge/delivery-contract.json` records this as a `known_gap` and
> `course-tablet-publisher/knowledge/platform.json` downgrades a remote font to `WARN`. Both reason
> about graceful degradation *in a browser*; neither knows the app returns 403.
>
> **Factory rule:** bundle `woff2` and declare `@font-face` from the asset root, or choose the system
> stack deliberately. No remote font, script, stylesheet or image, ever.

### 3.3 Hardware Back is driven by the page

`onBackPressedDispatcher` evaluates JavaScript in the page and clicks, in order:

1. `document.querySelector('a.gbt-topback[href]')`
2. `document.querySelector('.gbn-back')`, if its computed `display` is not `none`

If neither is found the callback disables itself and the default back runs — which **exits the app**.

> **Every reachable page must expose `a.gbt-topback[href]` or a visible `.gbn-back`.** A page that
> deliberately has no way back (the final assessment) uses an hrefless `<span id="gb-home">`, so the
> intent is legible to an audit instead of looking like a bug.

### 3.4 Offline is absolute, and there is no service worker

`allowFileAccess = false`, `allowContentAccess = false`. No CDN, no build step, no runtime fetch that
gates content. `domStorageEnabled = true`, so `localStorage` works — per application, and the trainee
and instructor APKs are different applications with separate WebView storage.

### 3.5 Old-WebView-safe JavaScript

`minSdk 24`. Shared engines are ES5: no arrow functions, no optional chaining, `keyCode` fallbacks
alongside `key`, `:has()` mirrored with a class. `gb_courses.js` uses `document.write` specifically so
a manifest resolves synchronously and never waits on a network.

### 3.6 Relative links only, and never outside the allowed root

No absolute `/assets/...`, no `file:///`, no `localhost`, no LAN IP outside `local_live/`. A relative
link that resolves above the terminal root is rejected by `assetPathFor()`.

### 3.7 Everything under an asset root is packaged into the APK

`.bak`, `.orig`, `__pycache__` and editor state ship to the device. An untracked new file is not
committed, and that failure appears only on the tablet, as a missing asset.

---

## 4 · How a course is discovered

Three layers; the first two are live.

**`gb_config.js` — the one file a build edits.** `COURSE`, `COURSE_ID`, `RUN_CODE`, plus the Supabase
URL and anon key. Every shell reads the course title and id from here.

**`courses/registry.js` — the installed-course list.** Generated by
`course-tablet-publisher/scripts/registry.py` by scanning each `courses/<id>/course.json`.
Deterministic and sorted, so two colleagues who both regenerate it produce identical bytes and a
textual conflict is resolved by re-running the generator, never by hand-merging.

```js
window.GB_COURSES = [
  {"id":"gas-basic","instructor":"","layout":"legacy","modules":8,
   "status":"released","title":"GAS BASIC","trainee":"","version":"1.0.0"}
];
```

**`gb_courses.js` — the manifest loader.** Given `data-load="gb_tasks.js"` it finds the registry entry
for `GB_CONFIG.COURSE_ID` and `document.write`s the script tag at the right prefix —
`courses/<id>/` for a pack, `""` for GAS BASIC at the root. Pages therefore do not know which layout
they are in.

> `registry.js`'s own header says *"Consumed by: nothing yet."* **That comment is stale** —
> `training_terminal/index.html` loads it and `gb_nav.js` reads `window.GB_COURSES` as a title
> fallback. Correct the comment the next time the file is regenerated.

### Two layouts

| Layout | Root | Status |
|---|---|---|
| **pack** | `training_terminal/courses/<course_id>/` | **Use for every new course** |
| legacy | files directly at the terminal roots | **GAS BASIC only — never create a second one** |

GAS BASIC predates the pack layout and *is* both terminals today. Converting it moves roughly 400
files and every relative link with them; that is a separate, human-authorised job.

### Required shape of a course pack (trainee root)

```
courses/<course_id>/
  course.json              id, title, modules, academic_hour_min, programme source, version
  module_NN/index.html     the one-page module: open, Start, Next to the end
  module_NN/tasks/         the trainee task pages that module's screens announce
  module_NN/assets/        that module's photos and figures + _photo_meta.json
  module_NN/documents/     optional - reference cards a trainee keeps
  module_NN/simulator/     optional - simulator briefs
  handout/index.html       the take-home, and the overflow valve for the accredited minutes
  assessment/              the final assessment, separate from every module check
```

Instructor side (`instructor_terminal/`): `it_run.js` (generated), `plans/`, `prepare/`, `record/`,
`checks/`.

**A course pack never reaches outside itself except to the shared engines.** Shared engines
(`gb_*.js`, `gb_*.css`, `style.css`, `radar.js`, `index.html`) live once at the terminal root and are
referenced, never copied. Copying is not hypothetical: `gb_done.js` currently exists as five identical
per-module copies.

---

## 5 · Generated files — never hand-edited

| File | Generated by | Why it matters |
|---|---|---|
| `instructor_terminal/it_run.js` | the course's `gen_it_run.py`, from each deck's own markup | Slide numbers move whenever a deck is cut. Hand-written references broke 96 cross-references in Modules 5 and 6 on 2026-09-02 — the instructor announced the wrong task, in the room. |
| `training_terminal/courses/registry.js` | `registry.py` | Conflicts are resolved by re-running, not merging. |
| `training_terminal/gb_tasks.js` | *was* generated; **is now hand-maintained** | Its own header warns that re-running `build_tablet_package.py` would revert hand-made corrections. Read the header before touching it. |

Anything a generator cannot derive belongs in an OVERRIDES table **inside the generator**, checked on
every run. A rotted override must stop the run rather than ship a wrong slide number.

---

## 6 · What is *not* in the APK

- **The decks.** `it_run.js` carries `deck: "Module_01/presentation/index.html"` and `it_content.js`
  names the same paths, but they appear only as data — no page links to them, and no `presentation/`
  folder exists anywhere under `app/src/**/assets`. The instructor terminal *describes* a deck the
  tablet cannot open.
  **Open question for the owner:** is the deck deliberately projected from a laptop while the tablet
  carries only the run script? It reads as intentional, but it is recorded nowhere.
- **PDFs.** The SME review and management overview PDFs live in the course tree, correctly outside the
  asset roots. Section 3.1 means they could not be opened from the app anyway.

---

## 7 · Checklist a generated course must pass

Ordered as the existing scripts run them.

1. Every page reachable from a front door, and every page has a way back (`gbt-topback` / `.gbn-back`)
   or declares that it does not — `audit_navigation.py`
2. Every link resolves **in the merged asset root** — `verify_links.py`
3. Deck ↔ run script ↔ tablet manifest agree on every task — `crosscheck_tasks.py`
4. Structure, counts, check → hand-off order — `verify_course.py`
5. No remote script, stylesheet, font or image
6. No non-HTML navigation target, no `target="_blank"`, no `window.open`, no `<input type="file">`
7. No `.bak` / `.orig` / `__pycache__` anywhere under an asset root
8. No instructor-only file inside the trainee tree — `gates.py` roles check
9. No credential beyond the Supabase **anon** key (a `service_role` key is a hard fail)
10. Only file extensions from the MIME allowlist in section 2

---

## 8 · Recorded for an owner decision — not acted on

| | |
|---|---|
| **A-1** | Raleway is fetched from Google Fonts and 403'd by the app on ~105 pages. Bundle it, or choose the system stack deliberately. |
| **A-2** | `gb_config.js` ships the Supabase **anon** key. Publishable by design — but the tablets make unauthenticated writes to `course_runs` and `unlocks`, so anyone who unzips the APK reaches those endpoints. Row-level security in `backend/` is the only thing protecting them. An RLS audit is worth doing; it is not the factory's job. |
| **A-3** | `gb_sync.js` derives the unlock scope with `/^modules\/(m\d)\//` — single digit. Two courses in one run would collide on `m1`, and a course with 10+ modules breaks. |
| **A-4** | Six module lists are duplicated (`GB_TASKS`, `IT_MODULES`, `IT_RECORD`, `live.js MODULES`, `practical_skills_record.html MODS`, `handout.js MODS`) and `handout.js` **already disagrees** with the other five. |
| **A-5** | `gb_config.js RUN_CODE = "GAS101"` is also a task code in `gb_tasks.js`. The same string means two things. |
| **A-6** | The decks' absence from the APK (section 6). |
