---
name: realistic-visuals
description: >
  Make REAL realistic, 3D, photo-like or cinematic pictures and short realistic/3D animation clips
  with Google Nano Banana (images) and Veo (video) through this plugin's MCP tools, and manage the
  whole job - every picture costs money, so first find the places a picture fits and ask the person
  to describe each one, show the prompt, generate only after their yes, open and check, package
  locally, place on the slide or screen, record provenance. Use whenever a presentation, deck, pptx, HTML slide,
  handout, poster or course screen asks for "3D", "realistic", "photorealistic", "render",
  "3D realistic animation", "cinematic", "like a photo", "product shot", "cutaway render", "hero
  image", "nano banana", "veo", or when a realistic scene is the right medium and no real
  photograph exists. Replaces hand-drawn SVG "realism" - never fake a render with gradients and
  shapes. NOT for labelled technical schematics, piping/circuit diagrams, charts, flowcharts or
  anything whose topology must be exact - those stay authored SVG/HTML.
---

# Realistic visuals — let the image model paint, and Claude run the job

**v2 · plugin `nano-banana` 1.2.0 - ask first, every picture costs money**

When somebody asks for a realistic or 3D picture, a language model's reflex is to draw one in SVG:
a gradient, some rounded boxes, a glow, a drop shadow. That is not a render, and everybody can see
it is not. This plugin gives Claude a real image model. **Claude stays the art director** — it
decides what the picture must show, writes the prompt, looks at every result, throws away the wrong
ones, and places the right one. Nano Banana only makes pixels.

Tools (MCP server `nano-banana`):

| Tool | Does |
|---|---|
| `generate_image` | still image — text-to-image, or edit/restyle/combine with `reference_images` |
| `generate_video` | 4–8 s mp4 clip with Veo 3.1, optionally starting from an approved still |
| `get_video` | collects a clip that was still rendering |
| `setup_api_key` | opens the key window, to set or change the key |
| `nano_banana_status` | is the key set, does it work, which models can it reach, how many pictures were made today and this month |

## 0 · Ask first - every picture costs money (owner, 2026-10-14)

Every generation is billed to the NOVIKONTAS Google account: **about €0.10 a picture**, and a video clip
costs much more. Four colleagues redoing pictures 10-15 times each use the budget up fast, and most redos
come from a vague first description. So **nothing is generated automatically.** The order is always:

1. **Find the places first.** Go through the deck or module and list every place where a generated picture
   really helps: a realistic scene that no real photograph shows, and that is not a schematic (§1). For each
   one: the slide number, the slide title, what the picture would show, and why it is generated rather than a
   photograph or a drawing. Show the list and let the person strike any place.
2. **Ask about one place at a time**, in plain words. For example:
   > On slide 3, *"Why gases are carried as liquids"*, I'd like to put a Nano Banana picture. Each picture
   > costs about €0.10, so please help me get the best result on the first try. Tell me what you want to
   > see. I've filled in my suggestion for each question; correct anything:

   1. **What is the main thing in the picture?** Exactly which ship, equipment or place: its type, size, condition.
   2. **Which parts must be clearly visible?**
   3. **From where do we look?** From above, from the side, close up, from the deck, from inside.
   4. **Where and when?** At sea, in port, in a workshop; day or night; the weather.
   5. **A real photograph look, or a 3D render look?**
   6. **What must not be in it?** People, text, the wrong kind of equipment, anything that would be untrue.
   7. **Where does the slide's text go?** Which part of the picture stays empty?
   8. **Do you have a photo that shows what you mean?** A reference picture helps the model more than anything.

   Give a suggestion for every question, drawn from the slide's own words, so the person only corrects.
   *"Your suggestion is fine"* is an answer.
3. **Write the prompt from their answers (§2) and show it** in one block, with the aspect ratio and the file it
   is saved to. Ask: *"Generate this one picture (about €0.10)?"*
4. **Generate only after a clear yes, and only once.** Pass their own words in `approved_by_user`; the tool
   refuses to run without them. Never write that field yourself, and never reuse an earlier yes for another
   picture or a redo. (1.3.1) Where the client offers a confirmation dialog (MCP elicitation) the person
   confirms there too; a decline is final - do not retry. A **spending cap** (EUR 5 a day, EUR 50 a month on
   this computer by default) refuses with how to raise it: tell the person, never raise it yourself. A video
   whose status check fails comes back `running` with its `operation` - collect it with `get_video`; the
   operation is also in `usage.jsonl` and in `nano_banana_status`.
5. **Show the result and ask:** use it, or what should change? A change is a new paid picture. Say what you
   would change and ask again. Prefer an edit of the good picture (`reference_images` and *"change only X"*) to
   a new one from scratch.
6. **Say what it cost so far**, in one line, from the tool's `cost.tell_the_person`:
   *"That's picture 4 today on this computer, about €0.40."*

A video clip follows the same steps. Say that it costs much more than a picture, and make and approve its
still first (§5). Inside a Course Factory course, `course-factory/scripts/picture_briefs.py` keeps each
module's places, the person's answers and every picture made, so a redo next week does not ask everything again.

**The key looks after itself.** The first time `generate_image` or `generate_video` runs without a
key, a small window opens on the user's screen. The user pastes the NOVIKONTAS shared key, and the
server checks and saves it. Before the first generation, tell the user in one line:
*"A small window will open asking for the Gemini key — paste it there (ask Raivis if you don't have it)."*
If they want to change the key, call `setup_api_key`. If a tool reports the window was closed or
could not open, pass its message on. **Never ask for the key in the chat, never write it into a
file yourself, never echo it.**

### The free route first: Gemini in the browser (1.3.0)

When a browser with a signed-in Gemini is there (Claude in Chrome, or the built-in browser pane), make the
pictures with the **`gemini-browser`** skill instead of these tools: the person's Google AI Pro account costs
nothing per picture, the places and prompts come from one list (`picture_briefs.py queue`), the person says go
once, and Claude drives the page, downloads each picture and moves it into the project. The tools below stay for
video, for reference-image edits the app cannot take, and when no browser is signed in.

### When Google says *free tier* or *billing*: the manual route

If a browser can be driven, use `gemini-browser` (above). Only without one:

The API has no free quota for image or video models, so a key without billing on its project comes
back `HTTP 429 … free_tier … limit: 0`. **After that error, stop calling the tools for the rest of
the session.** Retrying cannot help. **Do not fall back to drawing the picture in SVG.** Switch to
the manual route instead. A Google AI Pro subscription includes Nano Banana in the Gemini app at no
extra cost, so the user makes the picture and Claude runs everything around it:

1. Do the work as normal: decide, write the full prompt (§2), and pick the aspect ratio and the
   exact destination file.
2. Give the user **one copy-ready block per picture**: the prompt, the aspect ratio, and the exact
   path to save it to. For example:
   > Open **gemini.google.com** → *Create image* → paste the prompt → download the picture and save
   > it as `…/assets/lng_carrier_starboard_quarter.png`. Say **done** when it is there.
3. When they say done, pick up from §4. **Open the file and check it**, ask for a redo with a
   corrected prompt if it is wrong, then place it (§6) and write provenance with
   `"generated_by": "Gemini app (manual), Nano Banana"`.

Say once, in one line, why: *"Automatic generation is waiting for billing on the Gemini key, so this
time you make the picture in the Gemini app and I take it from there."* Never ask for the key and
never suggest a way around billing.

---

## 1 · Decide: generate, or draw?

| The picture must… | Use |
|---|---|
| look like a photograph, a 3D render, a real place, real equipment in context, a realistic scene, material and light | **`generate_image`** |
| show realistic motion — a camera orbit, a process running, weather, a crew doing something | **`generate_video`** (from an approved still) |
| show exact topology — which pipe joins which valve, flow direction, a circuit, a P&ID, labelled parts that are tested | **authored SVG/HTML** — never generated |
| carry numbers — a chart, a table, a trend | **authored** — never generated |
| be text — a definition, a limit, a quotation | **no picture** |

The hard line: **generated imagery never replaces a structured technical schematic.** A generator
invents plausible pipes. A cutaway *render* for atmosphere is fine; a cutaway whose parts the
learner is examined on is authored.

Mixed need is common and good: a realistic render as the base layer, the labels and arrows authored
on top in SVG/HTML. That is the best of both.

### Inside a Course Factory course

If the work is a NOVIKONTAS course module (the `course-factory` plugin is installed and the folder
is a course), this skill is **level 4 · CREATE → generated illustration** of that plugin's asset
pipeline, and its laws still apply:

- levels 1–3 (project files → factory library → a real licensed photo on the internet) come first —
  a real photograph of the real equipment beats any render;
- **no generation for safety-critical equipment the trainee must recognise in real life** — get a
  real photograph;
- the `GENERATED_ASSET_BRIEF.md` brief in `course-visuals` **is** the prompt source: turn its
  sections into the prompt below, and check the result against its §7 *forbidden inaccuracies*;
- animation must teach (`course-visuals` L13): what changes, why, what to notice, what is
  understood afterwards. A clip that only looks nice is decoration and is rejected.

Outside a course (a sales deck, a conference talk, a poster) the user's request rules: if they
asked for 3D or realistic, generate it.

---

## 2 · Write the prompt like a shot list, not a mood

A good prompt is a camera and a set, described plainly. Cover, in this order:

1. **Subject** — one subject, named exactly (type, size, era, condition). *"A 174 000 m³ membrane-type
   LNG carrier, loaded, at sea"* — not *"a big gas ship"*.
2. **What must be visible** — the parts that matter, so they are in frame and identifiable.
3. **Viewpoint** — camera height, angle, distance, lens. *"From 30 m off the starboard quarter, 15 m
   above the waterline, 35 mm lens."*
4. **Lighting and time** — *"overcast North Sea midday, soft light, no lens flare."*
5. **Style** — say it: *photograph*, *photorealistic 3D render*, *clean studio product render*,
   *technical cutaway illustration*, *isometric 3D*. One style per image.
6. **Background and space** — plain, contextual or dark; **leave empty space where the slide title or
   labels will sit** (say where: *"empty sky in the top third"*).
7. **Exclusions** — what the model is likely to get wrong, as plain *"no …"* statements: *"no text,
   no letters, no logos, no watermark, no people, no extra funnels, no spherical Moss tanks."*

Always include **"no text, no lettering, no logos"** — labels are added afterwards in HTML/SVG/PPTX
where they stay sharp, translatable and correctable. Never ask the model to write the words.

Consistency across a deck: make the first approved image, then pass it in `reference_images` for the
next ones with *"same visual style, lighting and colour grade as the reference"*.

Brand: if the deck is NOVIKONTAS, name the palette in the prompt only as light and colour grade
(e.g. *"cool navy and white colour grade"*) — never ask the model to draw the logo. Place the real
logo file afterwards.

---

## 3 · Generate with sensible defaults

| Destination | aspect_ratio | image_size |
|---|---|---|
| full-bleed slide / title slide | `16:9` | `2K` (`4K` if printed large) |
| half-slide image beside text | `4:3` or `3:4` | `2K` |
| tablet portrait screen | `3:4` or `9:16` | `2K` |
| square card, social | `1:1` | `1K`–`2K` |

Generate **once, at the final size**. A 1K draft and then a 2K final is two paid pictures.

Model: default Nano Banana 2 (`gemini-3.1-flash-image`). Switch to `model: "pro"`
(`gemini-3-pro-image`) for crowded scenes, fine mechanical detail, or after Flash failed twice.

Save **straight into the deck's or module's own assets folder**, lower snake_case, subject first:
`assets/lng_carrier_starboard_quarter.png`. Never leave the picture only in a temp folder.

---

## 4 · Look at it. Every time.

**Open every saved image with Read before using it.** Then check, honestly:

- Is it the subject asked for — the right type of equipment, not the thing it resembles?
- Is every *must be visible* item there and recognisable?
- Did any exclusion get violated — text, gibberish lettering, logos, extra parts, wrong count,
  impossible geometry, melted hands, floating objects?
- Is there space where the title/labels go?

Wrong → **tell the person** what is wrong and what you would change (a more specific prompt, the
violated item added to the exclusions, or an edit of this picture with *"change only X"*), and **ask
before generating again** (§0). Never regenerate on your own. If two pictures on the default model
missed, say that Pro (`model: "pro"`) handles fine detail better but costs more, and let them choose.
If it still cannot be done, say so. Do not ship a near-miss, and do not fall back to drawing it in SVG.

Small fixes are edits, not re-rolls: pass the good image in `reference_images` and describe only the
change (*"remove the text on the hull"*, *"make the sky overcast"*).

---

## 5 · Animation — still first, then motion

1. Make and approve the **key frame** with `generate_image` (16:9 or 9:16 — Veo takes only those).
2. `generate_video` with `start_image` = that file. Prompt **one shot, one action, one camera move**:
   *"Slow 20-degree orbit to the left around the ship, camera steady, sea moving gently, no cuts."*
3. Defaults: 8 s, 720p, Veo 3.1 Fast. `1080p`/`4k` need 8 s. Takes 1–6 minutes; if `get_video` is
   needed, call it with the returned `operation`.
4. Look at it: at least read the returned info and, if ffmpeg exists, pull 3 frames
   (`ffmpeg -i clip.mp4 -vf fps=1/3 frame_%d.png`) and Read them.
5. Google deletes its copy after 2 days — the local mp4 is the only copy.

Embedding:

- **HTML slide / tablet screen:**
  `<video src="assets/clip.mp4" poster="assets/clip_poster.png" muted playsinline loop preload="auto"></video>`
  — local file, poster = the key frame, `muted` (tablets block audible autoplay). Respect
  `prefers-reduced-motion`: show the poster, start on tap.
- **PowerPoint (python-pptx):** `slide.shapes.add_movie("assets/clip.mp4", left, top, width, height,
  poster_frame_image="assets/clip_poster.png", mime_type="video/mp4")`.

---

## 6 · Place it

- **Local files only.** Tablets and projector PCs are offline; the NOVIKONTAS tablet app refuses
  every remote host. Never hot-link.
- **HTML:** `<img src="assets/x.png" alt="<what it shows>">`, labels as positioned HTML/SVG on top.
- **PPTX:** `slide.shapes.add_picture(...)`; for full-bleed, size to the slide and send to back,
  title in the reserved empty space; keep text on a scrim if contrast is low.
- **Say it is AI-generated.** A small caption or footer: *"AI-generated illustration"*. Never present
  a generated image as a photograph of real equipment. (All outputs also carry Google's invisible
  SynthID watermark.)

### Provenance (always in a course, recommended elsewhere)

Beside the file, in `_figure_meta.json` in the same folder, keyed by filename:

```json
{
  "lng_carrier_starboard_quarter.png": {
    "origin": "generated illustration",
    "rights_state": "PROJECT_OWNED",
    "shows": "membrane LNG carrier at sea from the starboard quarter; no labels in pixels",
    "teaching_purpose": "<what the viewer should take from it>",
    "used_in": "<deck or module file and slide/screen>",
    "visually_verified": "yes - <what was seen, what was checked> <YYYY-MM-DD>",
    "generated_by": "nano-banana gemini-3.1-flash-image",
    "generation_brief": "<path to the brief, or the prompt itself>",
    "depicts_what_no_photograph_can": "<why a render rather than a photo>",
    "declared_as_drawing_on_page": true
  }
}
```

Never write `visually_verified: yes` for an image you did not open.

---

## 7 · Report back briefly

Per image or clip: path · model · attempts · what was checked · any caveat (*"funnel shape is
generic, not a specific yard design"*). If something could not be generated honestly, say so and say
what would unblock it (usually a real photograph).

Cost: every picture costs about €0.10 and a clip much more (§0). Nothing is generated without the
person's yes, nothing is redone without a new yes, no drafts before the final, and no video unless
motion was asked for or is clearly the right medium. Report the count and cost the tool returns.
