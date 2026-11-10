# {{LIBRARY_NAME}} - read me first

One shared knowledge base and asset library for every NOVIKONTAS course on its subject:
**{{SUBJECT}}**{{STCW}}. Made {{CREATED}} by the Course Factory (`subject_library.py create`) from its
library template. Each fact, picture and document is kept and checked once, here, and each course
takes what it needs.

## What is where

| Path | What it is |
|---|---|
| `catalog.html` | **Open this.** Every picture and document: search, filter, click for the provenance (after the first build). |
| `knowledge/FACTS.md` | The hard values the courses teach, with their sources; CONFLICT where sources disagree. |
| `knowledge/GLOSSARY.md` | Shared terms and abbreviations, with the source definition. |
| `knowledge/REGULATIONS.md` | Every regulation, code and guideline the library holds, which edition. |
| `knowledge/INBOX.md` | New facts, terms and regulations from course sessions, waiting for review (NEW). |
| `knowledge/topics.json` | The shared topic list and which module of each course teaches it. |
| `knowledge/synonyms.json` | Words that mean the same thing to a trainee, for the search. |
| `OPEN_DECISIONS.md` | The CONFLICT rows the owners still have to decide. |
| `documents/` | The original reference PDFs by type, with their **distribution** in `document_sources.json`: SHARE, FREE_DOWNLOAD, INSTRUCTOR_ONLY, CHECK. |
| `KNOWLEDGE_BASE/` | The documents made searchable (built by `tools/build_library.py` with the factory's `kb_build.py`). |
| `assets/` | The pictures, one copy each; `assets/ASSETS.json` holds their provenance. |
| `contributions/` | Pictures course sessions added with `tools/contribute.py`. |
| `courses/<course>.md` | Per course: what it uses and what the others have. |
| `library_config.json` | The library's name, subject, reviewers, courses and knowledge bases. |

## The quickest way in

```
python tools/find.py "<subject>"
python tools/use_asset.py <id> "<course>/modules/module03" --note "M03 slide s04"
python tools/build_library.py
```

## Rules

- **The course keeps its own copy** - `use_asset.py` copies the file and its provenance into the module.
- **No picture without provenance**, and only cleared rights states go on the tablets.
- **Real photos first** - never an AI image of equipment a trainee must recognise.
- **Facts are cited**; a CONFLICT is decided by the owners, never picked on a slide.
- **INSTRUCTOR_ONLY documents never go to trainees.**
