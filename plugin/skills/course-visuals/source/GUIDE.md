# Source — find the asset, or say honestly that it does not exist

Read this when you need an actual file: a photograph, a drawing, a manufacturer figure. The
authority is `knowledge/asset-pipeline.json`; this is how to run it.

---

## The law

**Levels run in order. A level is exhausted only when it has been searched — not when it has been
assumed empty.** "I could not think of one" is not a search, and neither is a single grep for the
requester's exact phrasing.

```
1 PROJECT   source_files/, operator assets, manuals, drawings, the course's own assets
2 FACTORY   ${CLAUDE_PLUGIN_ROOT}/resources/
3 INTERNET  only after 1 and 2 were actually searched
4 CREATE    SVG · HTML/CSS/JS · Canvas · programmatic · generated illustration
```

`scripts/resolve_asset.py` mechanises levels 1 and 2 and will emit `GENERATED_ASSET_REQUIRED` when
both come back empty. Level 3 is judgement — hand it to the **`visual-sourcer`** agent, which works
in isolated context so a long search does not fill the main conversation.

---

## Level 1 — project, and how to search it properly

The single most common failure is declaring an asset unavailable after one narrow search. Expand
the terms before concluding anything:

- the **equipment name**, plus its plural, hyphenated and unhyphenated forms, and its abbreviation
- the **manufacturer**, and the model
- **alternate and older terminology** — the term a manual from twenty years ago would have used
- the **system** the component belongs to, and the document that would document that system
- likely **figure captions** — drawings are captioned, not named
- **both spellings** — a British-spelled course searching an American-spelled corpus finds nothing

Search filenames *and* content. A drawing inside a PDF-derived folder is found by its caption, not
its filename.

**A project asset wins over everything.** It is already cleared, already correct for this operator's
equipment, and needs no rights decision.

---

## Level 2 — the factory library

`${CLAUDE_PLUGIN_ROOT}/resources/`. Already reviewed, already licence-clean, already tablet-tested.

**Reuse only if it is both technically correct for this subject and pedagogically right for this
need.** A near-miss reused to save time teaches the near-miss.

---

## Level 3 — the internet, and what counts as a source

Authority ranking, strongest first:

1. the **manufacturer** of the actual equipment
2. an **official organisation** or regulator
3. the **original manual** or standard
4. a recognised **technical or industry organisation**
5. another **credible technical source** — a university, a national laboratory, a technical museum
6. an **open media repository** with per-file licence and author metadata

**Not authority, at any rank:** SEO content farms and listicles · Pinterest-style aggregators and
image scrapers · stock-photo preview thumbnails · personal blogs with no named technical author ·
AI-generated image sites · any page that does not say where the image itself came from.

Record per candidate: **source · url_or_origin · rights_state · technical_relevance ·
intended_use · modification_permitted · attribution_required**.

**Download it.** A legally usable internet asset is packaged locally. The tablet has no network at
class time, and the Android app returns 403 to every host except the classroom backend — a remote
image is not a slow image, it is a broken one.

---

## Rights, and the one escalation that blocks

`asset-pipeline.json` → `rights_states`. Six states: `CLEARED` · `PROJECT_OWNED` ·
`PUBLIC_DOMAIN` · `ATTRIBUTION_REQUIRED` · **`RIGHTS_REVIEW_REQUIRED`** · `REJECTED`.

> **If usage rights are unclear, the state is `RIGHTS_REVIEW_REQUIRED` and the asset does not
> ship.** Do not resolve it by assumption, and do not quietly use it anyway.

This is not theoretical. Six publisher figures in the reference course are marked *not cleared for
issue or publication*, and they currently block that course from being issued. One quiet decision
became an organisational problem.

Acceptable for photographs: public domain, CC0, CC BY, CC BY-SA, or explicit written permission.
Not acceptable: NC, ND, "free to use" with no named licence, stock previews, or anything scraped
from a manufacturer site or a PDF without a rights decision.

---

## Verification — open the file and look at it

**Record that you looked, and when.** `visually_verified` reads `yes - <what was seen> <date>`, or
says plainly that it was not verified. Never write `yes` for a file nobody opened.

A file named for one ship type in the reference sourcing pass turned out to show a completely
different vessel. **A caption is not evidence of content**, and a plausible photograph of the wrong
equipment teaches false recognition — worse than no photograph at all.

Three honesty rules that come from the same pass:

- **Never contradict named equipment.** If the course names a manufacturer, the image shows that
  manufacturer's kit or is not captioned as it.
- **Caption a near-miss honestly.** "A product tanker, not a gas carrier" is a usable caption.
  Silence is not.
- **Never present a generated illustration as a photograph.**

---

## Provenance — beside the file, never in a central register

One metadata file per asset folder, keyed by filename:

| Folder | File | Schema |
|---|---|---|
| photographs | `_photo_meta.json` | `schemas/_photo_meta.schema.json` |
| figures, drawings, generated illustrations | `_figure_meta.json` | `schemas/_figure_meta.schema.json` |

A central register goes stale the first time somebody moves a file. A metadata file in the same
directory as the JPEGs does not.

`scripts/check_assets.py` validates both: every image has an entry, every entry has its required
fields, `visually_verified` is real, rights states are valid, and nothing sits at
`RIGHTS_REVIEW_REQUIRED`.

### Naming and format

lower snake_case, subject first, no module number, no spaces ·
JPEG q≈82, max 2200 px long edge, **minimum 1200 px** long edge ·
PNG only for flat-colour line art · **inline SVG** for anything authored.

Only these extensions render on the tablet: `jpg jpeg png svg webp gif mp4 webm`. Anything else is
served as `application/octet-stream` by the app's fixed MIME allowlist.

---

## Level 4 — create, and what to reach for

`asset-pipeline.json` → `levels[3].choose_by_teaching_need`. In short: **SVG** for topology, labels
and state; **HTML/CSS/JS** for state-driven process; **Canvas** only where SVG genuinely fails;
**programmatic generation** where precision or repeatability matters.

> **Do not use generated imagery in place of a structured technical schematic.** A diagram that must
> be accurate is authored, not sampled.

---

## `GENERATED_ASSET_REQUIRED`

When nothing suitable exists at any level and a realistic illustration genuinely is the right
medium, emit the marker **with a complete brief** — `schemas/GENERATED_ASSET_BRIEF.md`.

There is **no image-generation MCP in this plugin**, deliberately. The brief is the contract for
when there is one, and it is useful immediately: a human can take it to any generator, or
commission a photograph from it.

A brief without every field is not a brief. The forbidden-inaccuracies field is the one that stops
a generated image teaching something false, and it is the one most often left empty.

---

## What "done" looks like for this lane

- Every level actually searched, in order, and the search recorded — including the terms tried
- Every asset has a provenance entry beside it, with a real `visually_verified`
- Every rights state is one of the six, and none is left implicit
- Anything at `RIGHTS_REVIEW_REQUIRED` is reported to the owner, not shipped
- Every remote asset that is used has been **downloaded and packaged locally**
- Every `GENERATED_ASSET_REQUIRED` carries a complete brief
- `scripts/check_assets.py` runs clean, and its output was read
