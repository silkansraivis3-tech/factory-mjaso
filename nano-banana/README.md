# nano-banana — realistic and 3D visuals for decks and courses

A second plugin in the `novikontas-course-factory` marketplace. It gives Claude a real image model
(Google **Nano Banana**) and a real video model (Google **Veo 3.1**), so a request for a *3D*,
*realistic* or *photo-like* picture — or a short *realistic / 3D animation* — is answered with an
actual render instead of an SVG imitation of one. Claude still runs the whole job: it writes the
prompt, looks at every result, rejects the wrong ones, saves the right one next to the deck, and
places it.

| | |
|---|---|
| `server/nano_banana_mcp.py` | MCP server, **Python standard library only** — nothing to pip install |
| `skills/realistic-visuals/` | when to generate and when to draw, the prompt shot-list, the check-every-image loop, embedding in HTML and PPTX, provenance |
| `skills/gemini-browser/` | **free route (1.3.0):** drives gemini.google.com on the person's own Google AI Pro account - no key, no cost per picture - from a list decided beforehand, downloads each picture and moves it into the project |
| `scripts/gemini_driver.js` · `scripts/gemini_take.py` | the page driver (`GB.send / wait / download`) and the mover that takes the picture from Downloads to the slide's file and writes its `_photo_meta.json` record |
| `agents/image-director.md` | does a whole set of images or clips in isolated context and returns paths only |

Tools: `generate_image` · `generate_video` · `get_video` · `setup_api_key` · `nano_banana_status`.

## Install

Nothing separate. `course-factory` declares `nano-banana` as a **dependency**, so installing the
course factory installs this too — and colleagues who already have the factory get it on the next
marketplace auto-update (or `/reload-plugins`).

Standalone, if ever needed: `/plugin install nano-banana@novikontas-course-factory`.

**The key.** NOVIKONTAS uses one shared Gemini key, which Raivis hands out privately. Nobody
configures anything in advance. The first time someone asks for a realistic picture, a small window
opens on their screen. They paste the key there, the key is checked against Google, and it is saved
to `~/.config/nano-banana/gemini_api_key` in their own user profile. It never goes through the chat
and never goes into this repo (the repo is public). To change it: *"change the nano banana key"*
(tool `setup_api_key`).
Without a window, e.g. on a headless machine, set the environment variable `GEMINI_API_KEY` instead.
The course factory works with or without a key.

For the owner of the shared key: in Google AI Studio / Cloud Console, restrict the key to the
Generative Language API, set a budget alert, and rotate it if it ever leaks or someone leaves.

Needs `python` on the PATH (3.8+).

Check it works — ask Claude: *"nano banana status"*. It should report `key_works: true` and list
the image and Veo models your key can use.

## Every picture costs money - so Claude asks first

About **€0.10 a picture** on the NOVIKONTAS Google account; a video clip costs much more. Nothing is
generated automatically:

1. Claude finds the places where a generated picture really helps, and lists them.
2. For each place it asks you to describe the picture: the main thing, what must be visible, from where we
   look, where and when, photo or 3D look, what must not be in it, where the slide's text goes, and whether
   you have a reference photo. It fills in a suggestion for each, so you only correct.
3. It shows the prompt and asks: *"Generate this one picture?"* Only your yes starts it; the tool refuses
   to run without your words.
4. It shows you the result. A change is a new paid picture, so it asks again.
5. It tells you how many pictures this computer made today and this month, and roughly what they cost
   (the log is `~/.config/nano-banana/usage.jsonl`). Ask *"nano banana status"* at any time.
6. A hard cap stops generation at about EUR 5 a day or EUR 50 a month on this computer. To raise it, set
   `NANO_BANANA_DAILY_LIMIT_EUR` / `NANO_BANANA_MONTHLY_LIMIT_EUR` (in `~/.claude/settings.json` under `"env"`
   or as a Windows user environment variable) and restart Claude Code. Prices: `NANO_BANANA_EUR_PER_IMAGE`
   (0.10), `NANO_BANANA_EUR_PER_VIDEO` (1.50) - estimates; Google's billing page has the real amount.
7. If Claude Code shows MCP confirmation dialogs (elicitation), each generation also asks you there.

The key is saved as plain text in `~/.config/nano-banana/gemini_api_key`. On Windows the file is protected
only by your Windows account (chmod is a no-op there).

## Use

Just ask in plain words:

> Make the title slide a photorealistic 3D render of an LNG carrier at sea, overcast, space for the title at the top.

> Slide 7 needs a realistic 8-second animation of the camera orbiting the cargo manifold.

It will **not** generate labelled schematics, piping diagrams or charts — those stay authored, because
a generator invents plausible pipes. Inside a NOVIKONTAS course the `course-factory` asset pipeline
still comes first (real photo of the real equipment beats any render), and this plugin is its
level-4 *generated illustration* step.

## Defaults

| | |
|---|---|
| image model | `gemini-3.1-flash-image` (Nano Banana 2); `gemini-3-pro-image` (Pro) on request or after failures; a failed Pro request is tried once with Flash (1.3.2) |
| video model | `veo-3.1-fast-generate-preview`, 8 s, 720p, 16:9 |
| images | 16:9, 2K, PNG, saved into the deck's own `assets/` |

All outputs carry Google's invisible SynthID watermark and are captioned *AI-generated illustration*
where they are shown.
