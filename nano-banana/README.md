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
| `agents/image-director.md` | does a whole set of images or clips in isolated context and returns paths only |

Tools: `generate_image` · `generate_video` · `get_video` · `nano_banana_status`.

## Install

Nothing separate. `course-factory` declares `nano-banana` as a **dependency**, so installing the
course factory installs this too — and colleagues who already have the factory get it on the next
marketplace auto-update (or `/reload-plugins`).

Standalone, if ever needed: `/plugin install nano-banana@novikontas-course-factory`.

**The key.** NOVIKONTAS uses one shared Gemini key, handed out by Raivis privately. Claude Code asks
for it when the plugin is enabled and keeps it in the system credential store (never in
`settings.json`, never in this repo — the repo is public). The key is optional at install time, so
skipping it never disables the course factory; generation just reports that a key is missing. To
set or change it later: `/plugin` → **nano-banana** → **Configure**.

For the owner of the shared key: in Google AI Studio / Cloud Console, restrict the key to the
Generative Language API, set a budget alert, and rotate it if it ever leaks or someone leaves.

Alternative (e.g. the key is shared by several tools): set the environment variable
`GEMINI_API_KEY` for your user, and restart Claude Code.

Needs `python` on the PATH (3.8+).

Check it works — ask Claude: *"nano banana status"*. It should report `key_works: true` and list
the image and Veo models your key can use.

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
| image model | `gemini-3.1-flash-image` (Nano Banana 2); `gemini-3-pro-image` (Pro) on request or after failures |
| video model | `veo-3.1-fast-generate-preview`, 8 s, 720p, 16:9 |
| images | 16:9, 2K, PNG, saved into the deck's own `assets/` |

All outputs carry Google's invisible SynthID watermark and are captioned *AI-generated illustration*
where they are shown.
