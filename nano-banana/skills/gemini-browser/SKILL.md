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

**plugin `nano-banana` 1.4.0** · owner 2026-10-16: *the AI thought a long time about which picture to make and
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

`GB.state()` also says whether the *Images* tool is on and which aspect ratio is set. `GB.state().model` shows the mode (tested 2026-10-16 on the NOVIKONTAS Workspace account in *3.1 Pro*: a 16:9
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

Each row is its own tool call - never two in one `javascript_tool` call: a call that runs long times the browser
tool out.

| # | Call | Expect |
|---|---|---|
| a | `javascript_tool`: `await GB.prompt(<prompt>, {aspect: '<aspect>'})` | `{put: true, aspect}` - new chat, the *Images* tool switched on, the aspect ratio picked (1:1 · 9:16 · 3:4 · 4:3 · 16:9), the prompt in the box, not sent yet |
| b | `computer` `wait`, 3 s | - (2-3 s between putting the prompt in and pressing Send, always) |
| c | `javascript_tool`: `await GB.press()` | `{sent: true}` |
| d | `javascript_tool`: `await GB.wait()` - a new call each time while `done: false` | `{done: true, pictures: 1, size: ['1024x572']}` in 1-2 min (each call waits up to 15 s); `limit: true` → the daily limit below |
| e | **built-in browser pane:** `javascript_tool`: `await GB.show()` | `{shown: true, size, since, fits: true, cols, rows, tiles: [[x0, y0, x1, y1], ...]}` - the newest picture 1:1 over the whole pane |
| f | **pane:** one `browser_batch` with a `computer` `zoom` per tile, `region` = that tile exactly as `GB.show()` gave it, `scale` 1 | 2 captures for 16:9 (2 x 1), 4 for 4:3 (2 x 2) |
| g | **pane:** Bash: `python <nano-banana>/scripts/gemini_take.py stitch <save_as> --expect <size from e> --since <since from e> --aspect <aspect> --about "<about>" --prompt "<prompt>"` | `{ok: true, file, width, height}`; exit 1 = refused, nothing saved - see the problems below |
| e' | **Claude in Chrome:** Bash `gemini_take.py now` (a stamp), then `javascript_tool` `await GB.download()` | `{clicked: true}` |
| f' | **Chrome:** Bash: `python <nano-banana>/scripts/gemini_take.py take <save_as> --since <stamp> --about "<about>" --prompt "<prompt>"` | `{ok: true, ...}`; exit 1 = not there yet, run it again |
| h | `Read` the saved file | look at it - step 3 |
| i | course only: `picture_briefs.py done <course> --module N --slide <id> --file <rel> --approved "<the person's go>" --free` | the build sheet now names the picture; `--free` = no cost counted |

**Why two ways.** Nobody is at the PC, and the built-in browser pane has no way out for a picture: *Copy image* is
denied the clipboard (Gemini shows *"Something went wrong"*), *Download* opens a "where to save" dialog nobody
answers, and Gemini's own page rules (CSP) block sending it to a receiver on this computer. So there the picture is
shown 1:1 over the pane, zoomed tile by tile, and stitched back - the size Gemini shows (about 1024 px wide, enough
for a slide picture, soft as a full-screen 1920 px background). In the pane never click *Copy image* or
*Download*. Claude in Chrome downloads normally, at Gemini's full size. Never use *Share via Drive*: it asks to
connect Gemini to the person's Drive, an account permission.

`<nano-banana>` is this plugin's folder (the folder that holds `skills/` and `scripts/`). `stitch` takes the
newest captures since `GB.show()`'s `since` that are the size of that picture's tiles (the PNGs the pane leaves in
the session's `tool-results` folder; screenshots and small captures are not tiles), puts them in the order whose
edges meet best, and refuses - saving nothing - when the tiles do not make exactly the size `GB.show()` reported or
the picture is not the line's aspect; `take` moves the newest picture in `~/Downloads` made after the stamp and
fixes the extension to the real format. Both write `_photo_meta.json` beside it (`generated: true`, `description`,
`generation_prompt`) - the record the course compiler reads, so a generated picture shows no credit line.
`GB.prompt` takes the overlay away for the next picture; `GB.hide()` after the last one.

**Several photos in one picture** (a line asking for "a grid of six photos", "a row of three"): Gemini returns an
uneven collage. Make every panel its own picture - one line per panel, the panel's own subject with the same shot
recipe and ending, saved as `<save_as stem>_1.png`, `_2` ... in `working_claude/picture_briefs/parts/` (outside a
course: a `_parts` folder beside the list, never the assets folder) - then lay them out:
`python <nano-banana>/scripts/gemini_take.py grid <save_as> --cols C --rows R --aspect <aspect> <part 1> <part 2> ... --about "<about>" --prompt "<the panel prompts>"`
- even cells with white gaps, each picture filling its cell, row by row. Ask each panel in the aspect nearest its
cell: 3 x 2 in 16:9 → 4:3, 2 x 2 in 16:9 → 16:9, 2 x 2 in 4:3 → 4:3, 4 x 2 in 16:9 → 1:1, a row of three in
16:9 → 9:16 (`grid` prints the cell it used).

**Pace and Google's check.** One picture at a time, each finished and saved before the next is sent - normal use
of the app, nothing faster. Do not poke the page between steps (no extra scripts, no repeated clicks, no trying
other buttons). If `GB.wait()` or `GB.state()` returns `blocked` (Gemini shows *"Check your internet
connection"*; behind it Google's unusual-traffic check, `google.com/sorry`), **stop the loop at once**. It is a
CAPTCHA: never try to pass it, never slow down or vary clicks to slip under it. Say: *"Google wants to check this
browser - please open Gemini in the pane, answer its check, and say done. N pictures are saved, M are still in the
queue."* For a large batch, offer the API route (`realistic-visuals`, about €0.10 a picture) instead.

**The daily limit.** A Pro account makes about 45 pictures a day, and the Flash model stops at the same moment -
switching the model does not help. `GB.wait()` then returns `{limit: true, until: "7:42 PM", at:
"2026-11-05T19:42:00+02:00"}` (Gemini's *"You've reached your image-generation limit until ..."*). Stop the loop -
no more prompts - and schedule the resume yourself, nobody is at the PC: a one-time task in the desktop app's
scheduled tasks (`create_scheduled_task` with `fireAt` = `at` plus 5 minutes; when `at` is null, work the moment
out from `until`), its prompt complete on its own: *"Continue the Gemini pictures with the nano-banana
gemini-browser skill in the built-in browser pane: `picture_briefs.py queue <course> --module N` (or the list at
<path>) and make every picture still without one."* In a `/loop` session, `ScheduleWakeup` at that moment does the
same. Say: *"Gemini's picture limit until <until>: N saved, M still in the queue, it carries on at <time> by
itself (the app must be open then; if it is closed, it carries on when the app opens)."* A list longer than
about 40 pictures spans more than one day - say so when the list is shown.

Problems, each with its one fix:

- `GB.wait()` → `failed: "I am unable to generate or create images"` → the *Images* tool was off (a Workspace
  account answers this way without it): `GB.prompt` and `GB.press` again - it switches the tool on.
- `GB.wait()` → `failed: "I encountered an error doing what you asked"` → `await GB.retry()` (Gemini's own Redo →
  Try again), then `GB.wait()`. A second error → stop that picture and say so; a long prompt with several subjects
  (three tanks in one picture) failed this way twice on 2026-10-16 - one subject per picture is safer.
- `GB.wait()` → `failed: "...signed in..."` → step 0. `failed: "...limit..."` / *try again later* with no
  `limit: true` → stop the loop as for the daily limit, and try again in an hour.
- `GB.show()` → `fits: false` → the pane is smaller than the picture: `resize_window` to a little more than the
  picture (1100 x 820 for 1024 x 765), `GB.show()` again; `resize_window` preset `desktop` after the last picture.
- `stitch` exit 1 → it says why, and nothing was saved: too few tile captures since `since`, or tiles of another
  size (the zoom was not 1:1 - a region not exactly the tile, or a scale below 1). `GB.show()` again and zoom its
  tiles once more; refused twice → stop that picture and say so. *"the aspect ratio did not take"* → make the
  picture again (`GB.prompt` sets the ratio afresh).
- `GB.download()` → `clicked: false` → take **one** screenshot (scale 0.5), click the picture's download icon
  by hand. If a menu offers sizes, take the full size.
- `take` keeps exiting 1 → in the built-in pane nothing is ever saved: use `GB.show()` and `stitch` (e, f, g). In
  Chrome the browser saves elsewhere: ask where once, pass `--downloads <folder>`.
- `GB.prompt` → `no prompt box` → navigate to `https://gemini.google.com/app`, paste the driver again.
- `GB.prompt` → `no Upload and tools button` / `no Create image` / `no 16:9 in the aspect ratio menu` → Gemini
  changed a label: one `read_page` (filter interactive) of the prompt bar, say which label it has now; the driver
  matches by label, so the fix is one line there.

## 3 · Check every picture - once, honestly

Open it with `Read`. Check against the line in the list:
- the subject is the one asked for - the right type of equipment, not the thing it resembles;
- no lettering, gibberish text, logos, extra parts, wrong count, impossible geometry;
- the space for the slide's words is empty;
- the Gemini mark: pictures from the app may carry a small visible sparkle in a corner. Do not remove it; a
  corner under the slide's words or crop by the layout (`object-fit`) is fine. If it sits on the subject, say so.

Good → set `visually_verified` in `_photo_meta.json` to `"yes - <what was checked> <date>"`.
Wrong → name what is wrong and the one change, and make it again in the same chat with *"Change only: ..."*
(an edit keeps what was right): `GB.prompt("Change only: ...", {newChat: false, aspect: '<aspect>'})`, then the
loop from b. It costs nothing, but stop after **two** tries on one place and tell the person;
do not loop.

## 3b · On the slide - compile and look (learned on Drošības pamatkurss M02 s07, 2026-10-16)

- **Each thing drawn gets its own picture, right beside its own drawing** (owner: *"shouldnt all A, B, C have its
  own image?"*, *"put each picture next to the visualizations"*). Three tanks side by side in one drawing → a row of
  three pictures directly under it, one under each tank (`.m02-tankrow` in the IGF M02 drawing fragment).
- **No scrollbar on a slide, ever** (owner, 2026-10-16). A dense two-column slide has no room in the words column -
  a picture there made the slide body scroll by 8 px. Use the room the drawing column has spare; do not shrink the
  drawing (its labels keep their px size and collide). **A photograph is never shown smaller than about 200 px on
  screen**: where there is no room for that, it gets its own step, or a tap opens it full screen with its record.
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
