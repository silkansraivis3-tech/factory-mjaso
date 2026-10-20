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
2 SHARED    2a the subject library (the Gas Library first), 2b ${CLAUDE_PLUGIN_ROOT}/resources/
3 INTERNET  only after 1 and 2 were actually searched
4 CREATE    SVG · HTML/CSS/JS · Canvas · programmatic · generated illustration
```

`scripts/resolve_asset.py` mechanises levels 1 and 2 (2a through the library's own search, by
description) and says `GENERATED_ASSET_REQUIRED` when both come back empty — provisional until level 3 has also been searched, which is what
`source/schemas/GENERATED_ASSET_BRIEF.md` requires before a brief is written. Level 3 is judgement — hand it to the **`visual-sourcer`** agent, which works
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

## Level 2 — what is already shared

**2a · The subject library.** One knowledge base + asset library shared by every course on a subject,
kept on the company's Drive, never in this repository — the **NOVIKONTAS Gas Library** (GAS BASIC,
GAS ADVANCED, IGF Basic, IGF Advanced) is the first. `scripts/subject_library.py locate` says whether
this computer has one (`knowledge/subject-libraries.json`: the env var `NOVIKONTAS_SUBJECT_LIBRARIES`,
the library's own variable such as `NOVIKONTAS_GAS_LIBRARY`, then its default place, `G:\My Drive\Gas
Library` for Google Drive on Windows). None found = skipped without a word; nothing depends on it.

`resolve_asset.py` searches it through the library's own `find.py` — by **description, what it shows
and its teaching purpose**, with synonyms, never by file name — and gates it by rights:

- **found** only in a state that may ship on the tablets: `PUBLIC_DOMAIN` · `ATTRIBUTION_REQUIRED`
  (credit on the slide) · `CLEARED` · `OWNER_CLEARED` · `PROJECT_OWNED` · `GENERATED`;
- **blocked**, classroom reference until cleared: `UNKNOWN` · `PUBLICATION_FIGURE` ·
  `RIGHTS_REVIEW_REQUIRED` · `SEE_LICENCE`;
- **an AI picture is held back** unless `--allow-ai` says the need is a scene or a cutaway a camera
  cannot show. It is never the picture of equipment a trainee must recognise.

Take a library picture into the module with the library's `use_asset.py <id> <module folder>` (the
resolver prints the command) — the file and its provenance record travel together. Pictures sorted
from a knowledge base (`kbga_*`) were sorted from contact sheets: open one before it goes on a slide.

**2b · The factory library.** `${CLAUDE_PLUGIN_ROOT}/resources/`. Already reviewed, already
licence-clean, already tablet-tested.

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

There is **no image-generation MCP in this plugin**, deliberately — it lives in the sibling
**`nano-banana`** plugin of the same marketplace. When that is installed, ask the person to describe
the picture (its `realistic-visuals` §0 - every picture costs about €0.10, L47), turn the brief and
their answers into the prompt, show it, and generate with `generate_image` only after their yes
(the `image-director` agent for a set of approved ones). When it is not, the brief is still useful immediately: a human can take it to
any generator, or commission a photograph from it.

A brief without every field is not a brief. The forbidden-inaccuracies field is the one that stops
a generated image teaching something false, and it is the one most often left empty.

---

## Saving back — what one course finds, every course on the subject gets

When the module is on a subject library's subject (`scripts/subject_library.py covers "<programme
title, STCW ref, module titles>"`), everything new this lane adds goes into the library as well as
into the module — once it is packaged in the module with its provenance record:

| Found or made | Command (`scripts/subject_library.py contribute ...`) |
|---|---|
| a picture from level 3, a Novikontas photo, a generated render | `picture <the file in the module>` — reads its `_photo_meta.json` / `_figure_meta.json` record |
| a reference document (a PDF: SDS, manual, guidance) | `document <pdf> --type <type> --title ... --edition ... --origin-url <publisher page> --distribution SHARE\|FREE_DOWNLOAD\|INSTRUCTOR_ONLY\|CHECK` |

The library refuses a picture without source, rights_state, credit, description, teaching_purpose and
a real `visually_verified`, and flags an AI picture (it must be `GENERATED` and is listed for
replacement by a real photo where it shows equipment). A picture already in a module of a course the
library harvests is not copied — the rebuild takes it from the course. A duplicate (same sha256) is
reported, not added. The contribution rebuilds the library (about 30 s); after several, pass
`--no-rebuild` and run `subject_library.py sync` once. **Say in the report what was contributed.**
Facts and terms go back the same way — `course-factory`'s `script/GUIDE.md` §0.

## What "done" looks like for this lane

- Every level actually searched, in order, and the search recorded — including the terms tried
- Every asset has a provenance entry beside it, with a real `visually_verified`
- Every rights state is one of the six, and none is left implicit
- Anything at `RIGHTS_REVIEW_REQUIRED` is reported to the owner, not shipped
- Every remote asset that is used has been **downloaded and packaged locally**
- Every `GENERATED_ASSET_REQUIRED` carries a complete brief
- On a subject library's subject: every new picture and document is contributed back, and the report says which
- `scripts/check_assets.py` runs clean, and its output was read
