---
name: realistic-visuals
description: >
  Make REAL realistic, 3D, photo-like or cinematic pictures and short realistic/3D animation clips
  with Google Nano Banana (images) and Veo (video) through this plugin's MCP tools, and manage the
  whole job - brief, prompt, generate, open and check, reject and retry, package locally, place on
  the slide or screen, record provenance. Use whenever a presentation, deck, pptx, HTML slide,
  handout, poster or course screen asks for "3D", "realistic", "photorealistic", "render",
  "3D realistic animation", "cinematic", "like a photo", "product shot", "cutaway render", "hero
  image", "nano banana", "veo", or when a realistic scene is the right medium and no real
  photograph exists. Replaces hand-drawn SVG "realism" - never fake a render with gradients and
  shapes. NOT for labelled technical schematics, piping/circuit diagrams, charts, flowcharts or
  anything whose topology must be exact - those stay authored SVG/HTML.
---

# Realistic visuals — let the image model paint, and Claude run the job

**v1 · plugin `nano-banana` 1.0.0**

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
| `nano_banana_status` | is the key set, does it work, which models can it reach |

If a tool says there is no key: tell the user to add it themselves — `/plugin` → **nano-banana** →
**Configure** (the key goes to the system credential store), or set the `GEMINI_API_KEY`
environment variable — then restart Claude Code. **Never ask for the key in chat, never write it
into a file, never echo it.**

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
| draft while iterating | any | `1K` |

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

Wrong → say what is wrong, fix the prompt (be more specific, add the violated item to the
exclusions, or pass the bad image as a reference with *"change only X"*), and regenerate. **Three
attempts, then switch to `pro`; two more, then stop** and tell the user what the model cannot do —
do not ship a near-miss, and do not fall back to drawing it in SVG.

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

Cost awareness: images are cheap, video is not. Do not generate video unless motion was asked for or
is clearly the right medium, and draft stills at `1K` before the final `2K`/`4K`.
