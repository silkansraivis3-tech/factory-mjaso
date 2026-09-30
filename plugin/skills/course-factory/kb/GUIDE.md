# The knowledge base — read it, never write to it

Read this lane at **intake** (Stage 1) and whenever the course needs source material. Everything
here is done by one script, `kb/scripts/kb_tool.py`; run it, do not re-implement it.

## Two kinds, told apart by their files

| Kind | How it is recognised | What is in it |
|---|---|---|
| **Course Source Processor** (the owner's tool, current) | `SOURCE_MANIFEST.json` and `sources/` at the top, usually with `COURSE_INDEX.md`, `NEEDS_ATTENTION.md`, `search_index/` | one folder per source with `document.md`, `metadata.json`, `tables/`, `images/`; a search index with every piece's page and position |
| **docling** (older courses) | `00_INDEX/SOURCE_MANIFEST.json` | one folder per source with `content.md`, `chunks.jsonl`, `source_metadata.json` |

`kb_tool.py detect <folder>` says which. **Never read a `document.md` or `content.md` whole** — some
are over a megabyte. Search, then read the pieces the search returns.

## At intake

```
python kb/scripts/kb_tool.py sources <knowledge base> --course <course folder>
```

It lists every source and sorts out what would otherwise be cited twice or cited in the wrong edition:

- **exact copies** (the same file in several folders) — cited once; no question;
- **the same document in two file formats** (`.doc` and `.docx`) — the newer format is cited; no question;
- **editions of one publication** (MARPOL 2022 beside an older MARPOL; an acronym beside the full
  title; a misspelt publisher) — each becomes **one pop-up question, "which edition is current?"**,
  written ready to ask in `<course>/_factory/kb_sources.json`. Every question has a *"Different
  publications — keep all"* option, because two files can look alike and be two books.

Put the edition questions into the intake pop-up with the others (`knowledge/intake.json`). Record
each answer:

```
python kb/scripts/kb_tool.py decide <course folder> --keep "<path of the current edition>"
python kb/scripts/kb_tool.py decide <course folder> --different <group id>
```

From then on **only the current edition is cited**, and a search leaves the other out.

## Finding material

```
python kb/scripts/kb_tool.py search <knowledge base> "<what you are looking for>" --course <course folder>
```

It ranks the pieces with the knowledge base's own index and writes a **retrieval pack** — the
matching extracts in the source's own words, each with its file and page — into
`<course>/_factory/retrieval/`. Cite the file and page shown, never the pack. Search by more than one
phrasing: the equipment's other names, the abbreviation, the older term. A search that finds nothing
is a stated gap, and a stated gap is a good answer (L4).

## What never happens

- **Nothing is written inside the knowledge base** (L14). The owner's SEARCH program writes its packs
  into the knowledge base's own `retrieval/` folder; the factory writes into the course folder only,
  and refuses a course folder that sits inside the knowledge base.
- An IMO model course is a training requirement, never a source of fact (L22).
- A figure or table from a textbook or publisher is not copied — see L33.
