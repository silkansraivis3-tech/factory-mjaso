# {{LIBRARY_NAME}} - instructions for Claude

Shared knowledge base + asset library for every NOVIKONTAS course on its subject ({{SUBJECT}}).
Human overview: `00_READ_ME_FIRST.md`. It sits in the `Course Libraries` folder on the company's
Google Drive; `LIBRARIES.json` there lists every library. Always work on that copy.

## Finding things - always start here

```
python tools/find.py "<subject in plain words>"
```

One call returns topics (and which module of each course teaches it), cited facts, glossary,
regulations held, the unreviewed inbox, pictures (cleared first, with paths), reference documents
with their distribution, and the best source passages with file + page. `--json` for scripts.
Run it before reading any knowledge file and before searching the internet. From a course build,
`subject_library.py find` reads this library together with the others the course uses.

More passages on one subject: `python tools/search.py "<query>" --top 20 --out retrieval/<name>.md`.
No passages = the documents are not searchable yet (`tools/build_library.py --kb-builder <kb_build.py>`).

## Rules when using what you find

- **Facts:** quote a value only with its source (document, edition, page). A CONFLICT row is not
  settled - say so and point to `OPEN_DECISIONS.md` instead of picking a value. An inbox row marked
  NEW is not reviewed - check its source before using it.
- **Pictures:** `python tools/use_asset.py <id> <module folder>` so the provenance travels with the file.
  Only the rights states in `library_config.json` `ship_states` go on the tablets; the rest are
  classroom reference until cleared. Never an AI picture of equipment a trainee must recognise.
- **Documents:** give a trainee or put on the tablets only SHARE documents (FREE_DOWNLOAD: prefer the
  publisher's link); never INSTRUCTOR_ONLY; CHECK = ask.
- **Nothing found:** say so, then the course's own knowledge base, then the internet. Never invent a
  value or a source.

## Saving back what you found - `tools/contribute.py`

- **a picture:** `contribute.py picture <file> ...` - source, rights_state, credit, description,
  teaching_purpose, visually_verified required (from the `_photo_meta.json` beside the file, or flags).
- **a reference PDF:** `contribute.py document <pdf> --type ... --title ... --origin-url ... --distribution ...`
- **a fact, term or regulation:** `contribute.py fact|term|regulation "<subject>" "<value>" --source "<doc, edition, page>"` -
  goes to `knowledge/INBOX.md` as NEW. Never write into FACTS.md / GLOSSARY.md / REGULATIONS.md yourself.
- **a new course:** `contribute.py register-course <id> --title ... --owner ... --module-root ... --module-glob ...`

From a course build use `subject_library.py contribute ...` - it decides whether a finding belongs
here or in the Common library. No source or no rights = refused. A mistake: `contribute.py withdraw ...`.

## Keeping it current

After a course gains pictures, or a document is added: `python tools/build_library.py` (with
`--kb-builder` to make documents searchable). Topics go into `knowledge/topics.json`, synonyms into
`knowledge/synonyms.json`. Do not edit generated files by hand: `assets/ASSETS.json`,
`knowledge/SOURCES.json`, `documents/DOCUMENTS.json`, `LIBRARY_INDEX.md`, `CHECKS.md`, `catalog.html`,
`courses/*.md`.
