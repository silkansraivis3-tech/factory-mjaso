---
name: gemini-browser
description: >
  Make Nano Banana pictures in the Gemini app (gemini.google.com) by driving the browser on the person's own
  Google AI Pro account - no API key, no cost per picture - and put each one straight into the project: the
  slide's own file, its record, the build sheet. Use whenever pictures are to be made for a deck, course module,
  handout or screen and a browser with a signed-in Gemini is there (Claude in Chrome, or the built-in browser
  pane), or when the person says "use Gemini in the browser", "no API", "free", "generate in Gemini", "download
  from Gemini", or the API answered free_tier / billing. The places and prompts are decided BEFORE the browser
  opens (picture_briefs.py queue in a course), so the model never deliberates which picture to make. NOT for
  labelled schematics, P&IDs, charts or anything a trainee is examined on - those stay authored SVG/HTML.
---

# Gemini in the browser - pictures without the API

**plugin `nano-banana` 1.3.0** · owner 2026-10-16: *the AI thought a long time about which picture to make and
where - decide that first, then drive Gemini in the browser, download, and put it in the project.*

The Gemini app on a Google AI Pro account includes Nano Banana at no cost per picture. Claude drives the page;
the person only signs in once, themselves.

## The one rule that saves the time

**The list is the decision.** Places, prompts, aspect ratios and file names are fixed in step 1. During the loop
do not re-decide places, compare options, rewrite prompts or "improve" a working prompt. A prompt changes only
when the person corrects it, or when a result failed the check in step 3 - then change the one thing that failed.

## 0 · Which browser, signed in

1. **Claude in Chrome** (the person's own Chrome, already signed in to Google) if its tools reach a browser.
2. Otherwise the **built-in browser pane**: open `https://gemini.google.com/app`. The person signs in there
   once; the pane keeps the login for later sessions.

**Never type a password, never ask for one in the chat, never store one.** Not signed in → say:
*"Please sign in to Gemini in the browser (top right, Sign in) with the Pro account, then say done."*
A cookie banner → *Reject all*.

Read [`scripts/gemini_driver.js`](../../scripts/gemini_driver.js) once and paste its whole text into one
`javascript_tool` call on the Gemini tab. It defines `GB` and returns `GB.state()`. Paste it again only after
the tab reloads (`GB is not defined`).

`GB.state().model` shows the mode (tested 2026-10-16 on the NOVIKONTAS Workspace account in *3.1 Pro*: a 16:9
picture in about 1.5 min). Leave the person's choice; suggest *Pro* once if two pictures missed on detail.

## 1 · The list - before the browser does anything

- **In a Course Factory course:**
  `python <course-factory>/scripts/picture_briefs.py queue <course> --module N`
  prints every place still without a picture: slide, title, the prompt (the person's saved one, or drafted from
  the approved script by the recipe in `media-and-tasks.json` → `generation_brief.gemini_browser`), the aspect
  ratio and the exact file. It writes `working_claude/picture_briefs/M0N.gemini.json`.
- **Anywhere else:** write the same list yourself - one line per picture: place, prompt (shot list from
  `realistic-visuals` §2, ending *"No text, no letters, no numbers, no labels, no logos, no watermark. Aspect
  ratio 16:9."*), file path in the project's own assets folder.

Show the list **once**, as it is printed, and start straight away - **no question before each picture, before
each download or before the list** (owner, 2026-10-16: *"dont have any confirmation, just download it and put it
in"*). The pictures cost nothing and land only in the project's own files. The person may stop or correct a line
at any time; a correction is saved (`picture_briefs.py save --slide <id> --brief <json>`) and that picture made
again. If your browser tool itself insists on a yes for downloads, ask once for the whole list - never per picture.

## 2 · The loop - per picture, no thinking between steps

| # | Call | Expect |
|---|---|---|
| a | `javascript_tool`: `await GB.send(<prompt>, {aspect: '<aspect>'})` | `{sent: true}` - new chat, the *Images* tool switched on, the aspect ratio picked (1:1 · 9:16 · 3:4 · 4:3 · 16:9) |
| b | `javascript_tool`: `await GB.wait()` - again while `done: false` | `{done: true, pictures: 1, size: [...]}` in 1-2 min (each call waits up to 38 s) |
| c | **built-in browser pane:** `find` "Copy image" → `computer` `left_click` on that ref - a **real** click (a script click is not allowed to write the clipboard) | - |
| d | **pane:** Bash: `python <nano-banana>/scripts/gemini_take.py clip <save_as> --expect <size from b> --about "<about>" --prompt "<prompt>"` | `{ok: true, file, width, height}`; exit 1 = the copy did not land (the clipboard holds an older picture): hover the picture, click Copy image once more |
| c' | **Claude in Chrome:** Bash `gemini_take.py now` (a stamp), then `javascript_tool` `await GB.download()` | `{clicked: true}` |
| d' | **Chrome:** Bash: `python <nano-banana>/scripts/gemini_take.py take <save_as> --since <stamp> --about "<about>" --prompt "<prompt>"` | `{ok: true, ...}`; exit 1 = not there yet, run it again |
| f | `Read` the saved file | look at it - step 3 |

**Why two ways (tested 2026-10-16):** the built-in browser pane takes the *Download* click and saves nothing, so
there the picture goes through the clipboard - the size Gemini shows (about 1024 px wide, enough for a slide
picture, soft as a full-screen 1920 px background). Claude in Chrome downloads normally, at Gemini's full size.
Never use *Share via Drive*: it asks to connect Gemini to the person's Drive, an account permission.
| g | course only: `picture_briefs.py done <course> --module N --slide <id> --file <rel> --approved "<the person's go>" --free` | the build sheet now names the picture; `--free` = no cost counted |

`<nano-banana>` is this plugin's folder (the folder that holds `skills/` and `scripts/`). `clip` saves the
clipboard picture (and refuses the one it saved last time); `take` moves the newest
picture in `~/Downloads` made after the stamp and fixes the extension to the real format. Both write
`_photo_meta.json` beside it (`generated: true`, `description`, `generation_prompt`) - the record the course
compiler reads, so a generated picture shows no credit line.

**Pace and Google's check.** One picture at a time, each finished and saved before the next is sent - normal use
of the app, nothing faster. Do not poke the page between steps (no extra scripts, no repeated clicks, no trying
other buttons). If `GB.wait()` or `GB.state()` returns `blocked` (Gemini shows *"Check your internet
connection"*; behind it Google's unusual-traffic check, `google.com/sorry`), **stop the loop at once**. It is a
CAPTCHA: never try to pass it, never slow down or vary clicks to slip under it. Say: *"Google wants to check this
browser - please open Gemini in the pane, answer its check, and say done. N pictures are saved, M are still in the
queue."* For a large batch, offer the API route (`realistic-visuals`, about €0.10 a picture) instead.

Problems, each with its one fix:

- `GB.wait()` → `failed: "I am unable to generate or create images"` → the *Images* tool was off (a Workspace
  account answers this way without it): `GB.send` again - it switches the tool on.
- `GB.wait()` → `failed: "I encountered an error doing what you asked"` → `await GB.retry()` (Gemini's own Redo →
  Try again), then `GB.wait()`. A second error → stop that picture and say so; a long prompt with several subjects
  (three tanks in one picture) failed this way twice on 2026-10-16 - one subject per picture is safer.
- `GB.wait()` → `failed: "...signed in..."` → step 0. `failed: "...limit..."` / *try again later* → stop the
  loop, tell the person how many are done, the rest stay in the queue for later.
- `GB.download()` → `clicked: false` → take **one** screenshot (scale 0.5), click the picture's download icon
  by hand. If a menu offers sizes, take the full size.
- `take` keeps exiting 1 → in the built-in pane nothing is ever saved: use `clip` (c, d). In Chrome the browser
  saves elsewhere: ask where once, pass `--downloads <folder>`.
- `send` → `no prompt box` → navigate to `https://gemini.google.com/app`, paste the driver again.

## 3 · Check every picture - once, honestly

Open it with `Read`. Check against the line in the list:
- the subject is the one asked for - the right type of equipment, not the thing it resembles;
- no lettering, gibberish text, logos, extra parts, wrong count, impossible geometry;
- the space for the slide's words is empty;
- the Gemini mark: pictures from the app may carry a small visible sparkle in a corner. Do not remove it; a
  corner under the slide's words or crop by the layout (`object-fit`) is fine. If it sits on the subject, say so.

Good → set `visually_verified` in `_photo_meta.json` to `"yes - <what was checked> <date>"`.
Wrong → name what is wrong and the one change, and make it again in the same chat with *"Change only: ..."*
(an edit keeps what was right). It costs nothing, but stop after **two** tries on one place and tell the person;
do not loop.

## 3b · On the slide - compile and look (learned on Drošības pamatkurss M02 s07, 2026-10-16)

- **Each thing drawn gets its own picture, right beside its own drawing** (owner: *"shouldnt all A, B, C have its
  own image?"*, *"put each picture next to the visualizations"*). Three tanks side by side in one drawing → a row of
  three pictures directly under it, one under each tank (`.m02-tankrow` in the IGF M02 drawing fragment).
- **No scrollbar on a slide, ever** (owner, 2026-10-16). A dense two-column slide has no room in the words column -
  a picture there made the slide body scroll by 8 px. Use the room the drawing column has spare, and keep the
  pictures small (about 76 px high at 1280 x 800); do not shrink the drawing (its labels keep their px size and
  collide). A tap opens each one full screen with its record.
- On a stepped slide a picture that would give the answer away comes with its own step, never before: "predict,
  then reveal" is spoiled by a picture of the answer (CSS `:has(.<steptext>[data-step="N"].cur)`). A picture may
  fade with its drawing's part while another part is talked about.
- **A drawing with no room beside it** (a deck plan and a section filling the column, M02 s13): the picture lies on
  an empty part of the drawing, inside its own step's `<g class="pt">` as `<foreignObject class="..."><img ...>`,
  hidden except while that step is current. `gb_zoom.js` opens an `<img>` in a `<foreignObject>` on its own (2.45.0),
  not the whole drawing.
- **A real photograph already in the module beats a generated one**: the membrane tank (Wikimedia) and the
  Viking Grace LNG tanks moved under / onto their drawings; Gemini only for what no camera shows (the integral tank
  inside the hull, the cofferdam between engine room and fuel hold).
- **Equipment a trainee must recognise** (an airlock, a bunkering station, a bolted hatch, a drip tray - an
  `annotated_photo` in the script) gets a real photograph, never a generated one: it is on `PHOTOS_TO_TAKE.md`.
- `compile_module.py` must report nothing to fix (it now reports `scrolls`), then look at the slide at every step.
- A picture the person made in their own browser: `gemini_take.py put <picture> <save_as> --about "..."`, then
  `picture_briefs.py done ... --free`.

## 4 · Report

One line per picture: slide · file · size · tries · what was checked. Then: *"N made, M still in the queue."*
Compile the module afterwards so the pictures are on their slides.

## Where a generated picture goes (decided by the queue, not here)

| The slide is… | The generated picture |
|---|---|
| an AI illustration in the script (a scene no photograph shows) | **is** the slide's picture (`"figure"`), 16:9 |
| a drawing - schematic, cutaway, comparison, interactive diagram, step animation (tank types and barriers, hazardous zones, the A-60 plan) | goes **under the drawing** (`"inset": {"photo": ..., "under": "figure"}`), 4:3, a 3D render of the real thing. The drawing stays: its labels and boundaries are what the trainee is checked on, and a generator garbles words and invents pipes (owner, 2026-10-16: *"i need images there aswell"*) |
| real equipment a trainee must recognise | none - a real photograph |
| numbers, a chart, a flow animation | none |

A drawing slide that a picture would not help gets `"no_picture": true` in the build sheet, and the queue leaves it.
