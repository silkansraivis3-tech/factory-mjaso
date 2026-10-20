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

**On a shared subject library's subject** (the Gas Library for every gas course; `intake.json` → *the
subject library*), `course-visuals/scripts/subject_library.py find "<subject>"` comes before this
lane's search: it searches this course's knowledge base together with the other courses' and adds the
cited facts, glossary and open conflicts. This lane is still how a course's own knowledge base is
found, recorded and searched in depth.

First find it — the operator gives a course folder, not a knowledge-base path:

```
python kb/scripts/kb_tool.py find <course folder>
```

It looks in the course folder, every sub-folder and one level up, recognises each knowledge base by
its files, never walks inside one, and **writes nothing**. One found: use it. Several: `--json` gives
a ready pop-up question, "which one is this course's?".

**None found: the factory suggests making one — unasked** (owner, 2026-10-16: *"before creating any
module the AI should have already ... suggested for KNOWLEDGE_BASE to be created"*). `find` prints the
suggestion ready to pass on in plain words (L25): what a knowledge base is, which of the folder's files
it would be built from (programme, model course, codes, old course, `source_files`), how, and what the
course loses without it; `--json` carries it as `suggestion` with the ready pop-up question.
**How it is made:** the factory has no tool that builds one — never say or imply it does. The **Course
Source Processor** (Raivis Silkans's tool, outside the factory) is run on the `source_files` folder and
writes a `KNOWLEDGE_BASE` folder there. If the operator does not have it, they ask Raivis for it.

Record the answer once — no module starts without it (`scripts/course_gate.py`):

```
python kb/scripts/kb_tool.py decision <course folder> --built "<the new KNOWLEDGE_BASE>"
python kb/scripts/kb_tool.py decision <course folder> --yes "<a knowledge base they point to>"
python kb/scripts/kb_tool.py decision <course folder> --declined "<their reason, in their words>"
```

A found one is recorded with `--yes` too. A declined knowledge base is allowed; the Stage 2 page keeps
showing it, and the facts are then searched in the source files themselves.

Then sort its sources:

```
python kb/scripts/kb_tool.py sources <knowledge base> --course <course folder>
```

It lists every source and sorts out what would otherwise be cited twice or cited in the wrong edition:

- **exact copies** (the same file in several folders) — cited once; no question;
- **the same document in two file formats** (`.doc` and `.docx`) — the newer format is cited; no question;
- **editions of one publication** (MARPOL 2022 beside an older MARPOL; an acronym beside the full
  title; a misspelt publisher) — each becomes **one pop-up question, "which edition is current?"**,
  written ready to ask in `<course>/working_claude/kb_sources.json`. Every question has a *"Different
  publications — keep all"* option, because two files can look alike and be two books.

`kb_sources.json` is rewritten only when what it holds changes — running `sources` again on an unchanged
knowledge base leaves the file (and its date) alone. A course with several knowledge bases keeps one entry
per knowledge base (`knowledge_bases`); a run on one never drops the others. The top level stays flat (the
union of all) for `decide`.

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
`<course>/working_claude/retrieval/`. Cite the file and page shown, never the pack. Search by more than one
phrasing: the equipment's other names, the abbreviation, the older term. A search that finds nothing
is a stated gap, and a stated gap is a good answer (L4).

Searching is a read: it writes only its own retrieval pack — never `kb_sources.json` or `intake.json` — and
an agent that must not touch the course at all adds `--stdout`, which prints the pack and writes nothing.
Do not run `sources` before every search; run it once per knowledge base.

## What never happens

- **Nothing is written inside the knowledge base** (L14). The owner's SEARCH program writes its packs
  into the knowledge base's own `retrieval/` folder; the factory writes into the course folder only,
  and refuses a course folder that sits inside the knowledge base.
- **No course folder is made up** (2.48.1). `--course` must be an existing master folder or its
  `course\` folder, outside the factory and outside every knowledge base or `knowledge_base*` folder.
  A wrong one stops with nothing written and names the folder it should have been. (Before, a wrong
  `--course` was taken as it was and created - packs landed in the factory repo and beside a knowledge base.)
- An IMO model course is a training requirement, never a source of fact (L22).
- A figure from the knowledge base - a textbook or publisher figure too - **is usable as it is** (owner, 2026-10-01;
  L33 revised): credit it where the source is known and list it in `factory-notes.md`. Its images are in each
  source's `images\` folder.
