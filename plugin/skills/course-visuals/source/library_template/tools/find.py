"""Everything this library knows about a subject, in one call. START HERE (Claude and people).

    python tools/find.py "<subject in plain words>"
    python tools/find.py "<subject>" --pictures 12 --passages 8
    python tools/find.py "<subject>" --json                   # for scripts
    python tools/find.py "<subject>" --json --only pictures   # the factory's asset resolver (about 1 s)
    python tools/find.py "<subject>" --out retrieval/<name>.md

Answers, in this order, each with where it comes from:
  1. Topics      - which shared topic(s) and which module of each course teaches it
  2. Facts       - cited values from knowledge/FACTS.md (CONFLICT rows are flagged - do not quote them
                   until the owners decide, OPEN_DECISIONS.md)
  3. Glossary    - the definition and its source (knowledge/GLOSSARY.md)
  4. Regulations - which regulation / edition the library holds (knowledge/REGULATIONS.md)
     Inbox       - facts, terms and regulations course sessions added (knowledge/INBOX.md,
                   tools/contribute.py); NEW rows are not reviewed yet
  5. Pictures    - library assets with rights state; cleared ones first; copy one into a module with
                   tools/use_asset.py <id> <module folder>
  6. Documents   - the reference PDFs held, with their distribution (SHARE / FREE_DOWNLOAD /
                   INSTRUCTOR_ONLY / CHECK)
  7. Passages    - best source passages from all knowledge bases (file + page), duplicates removed
Synonyms (glossary + knowledge/synonyms.json) are applied.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import libconfig as C  # noqa: E402
import search as S  # noqa: E402

LIB = C.LIB
CLEARED = C.SHIP_STATES


def load(rel, key):
    p = LIB / rel
    try:
        return json.loads(p.read_text(encoding="utf-8")).get(key) or []
    except (OSError, ValueError):
        return []


def rx(phrases):
    alts = sorted({re.escape(p) for p in phrases if len(p) > 1}, key=len, reverse=True)
    # whole words, plural allowed
    return re.compile(r"(?<![a-z0-9])(" + "|".join(alts) + r")(?:e?s)?(?![a-z0-9])", re.I) if alts else None


def md_rows(path, pattern, limit, first_cell_only=False):
    """Table rows of a markdown file that match, with the nearest heading."""
    if not path.exists() or not pattern:
        return []
    out, heading = [], ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            heading = line.lstrip("# ").strip()
            continue
        if not line.startswith("| ") or line.startswith("|---") or re.match(r"\|\s*(Term|Fact|Title|#)\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        hay = cells[0] if first_cell_only else line
        m = pattern.findall(hay)
        if m:
            out.append((len(m) + (3 if pattern.search(cells[0]) else 0), heading, cells))
    out.sort(key=lambda x: -x[0])
    return out[:limit]


def topics_for(phrases, words):
    hits = []
    query_text = " " + " ".join(phrases).lower() + " "
    for top in load("knowledge/topics.json", "topics"):
        hay_words = set(S.words(top["title"] + " " + " ".join(top.get("keywords", []))))
        n = 2 * sum(1 for k in top.get("keywords", []) if len(k) > 3 and k in query_text)
        n += sum(1 for w in set(words) if len(w) > 3 and w in hay_words)
        if n >= 2:
            hits.append((n, top))
    hits.sort(key=lambda x: -x[0])
    return [h[1] for h in hits[:3]]


def pictures_for(phrases, words, topic_ids, limit):
    pat = rx(phrases)
    scored = []
    for a in load("assets/ASSETS.json", "assets"):
        hay = " ".join(str(a.get(k) or "") for k in ("id", "description", "shows", "teaching_purpose")).lower().replace("_", " ")
        phrase = len(pat.findall(hay)) if pat else 0
        hay_words = set(S.words(hay))
        asked = {w for w in words if len(w) > 3}
        hits = sum(1 for w in asked if w in hay_words)
        s = 4 * phrase + hits
        if not s:
            continue  # a picture must say what was asked; sharing a topic is not enough
        a["_match"] = {"phrase": phrase, "words": hits, "of": len(asked)}
        s += sum(1 for t in a.get("topics", []) if t in topic_ids)
        if a["rights_state"] in CLEARED:
            s += 2
        if a["kind"] == "photo":
            s += 1
        scored.append((s, a))
    scored.sort(key=lambda x: -x[0])
    return [a for _, a in scored[:limit]]


def load_documents():
    docs = load("documents/DOCUMENTS.json", "documents")
    by_doc_id = {}
    by_file = {d["file"]: d for d in docs}
    for s in load("knowledge/SOURCES.json", "sources"):
        d = by_file.get(s.get("library_document"))
        if d:
            for c in s["copies"]:
                by_doc_id[c["doc_id"]] = d
    return docs, by_doc_id


def documents_for(docs, phrases, words, topic_ids, limit=5):
    pat = rx(phrases)
    scored = []
    for d in docs:
        hay = f"{d['title']} {d.get('note') or ''} {d['doc_type']}".lower()
        s = 4 * len(pat.findall(hay)) if pat else 0
        hay_words = set(S.words(hay))
        s += 2 * sum(1 for w in set(words) if len(w) >= 3 and w in hay_words)
        if not s:
            continue
        s += sum(1 for t in d.get("topics", []) if t in topic_ids)
        scored.append((s, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def snippet(text, pat, width=420):
    text = re.sub(r"\s+", " ", text or "").strip()
    m = pat.search(text) if pat else None
    start = max(0, (m.start() if m else 0) - width // 3)
    return ("..." if start else "") + text[start:start + width] + ("..." if start + width < len(text) else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--pictures", type=int, default=8)
    ap.add_argument("--passages", type=int, default=6)
    ap.add_argument("--facts", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--only", help="comma list of sections, e.g. 'pictures' or 'facts,glossary' - the others are "
                                   "left empty (without 'passages' no knowledge base is read)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    want = {s.strip() for s in a.only.split(",")} if a.only else None
    on = lambda s: want is None or s in want  # noqa: E731

    phrases = S.expand(a.query)
    words = [w for w in S.words(" ".join(phrases)) if w not in S.GENERIC]
    pat = rx(phrases)
    topics = topics_for(phrases, words)
    tids = {t["id"] for t in topics}
    K = LIB / "knowledge"
    facts = md_rows(K / "FACTS.md", pat, a.facts) if on("facts") else []
    gloss = (md_rows(K / "GLOSSARY.md", pat, 5, first_cell_only=True) or
             md_rows(K / "GLOSSARY.md", pat, 5)) if on("glossary") else []
    regs = md_rows(K / "REGULATIONS.md", pat, 5) if on("regulations") else []
    inbox = md_rows(K / "INBOX.md", pat, 5) if on("facts") or on("glossary") or on("regulations") else []
    pics = pictures_for(phrases, words, tids, a.pictures) if on("pictures") else []
    docs, doc_of = load_documents() if on("documents") or on("passages") else ([], {})
    dmatch = documents_for(docs, phrases, words, tids) if on("documents") else []
    _, hits, n = S.search(a.query, a.passages, quiet=a.json) if on("passages") else (None, [], 0)
    searchable = bool(n) if on("passages") else None
    for _, c in hits:  # the originals behind the passages are listed too
        d = doc_of.get(c.get("doc_id"))
        if d and d not in dmatch:
            dmatch.append(d)

    if a.json:
        print(json.dumps({
            "library": C.NAME, "library_id": C.CFG.get("library_id"),
            "query": a.query, "also_searched_as": phrases[1:],
            "searchable": searchable, "not_searchable": None if searchable or searchable is None else C.kb_hint(),
            "topics": [{"id": t["id"], "title": t["title"], "courses": t.get("courses", {})} for t in topics],
            "facts": [{"section": h, "row": c} for _, h, c in facts],
            "glossary": [c for _, _, c in gloss],
            "regulations": [c for _, _, c in regs],
            "inbox_not_reviewed": [c for _, _, c in inbox],
            "pictures": [{"id": p["id"], "kind": p["kind"], "rights_state": p["rights_state"],
                          "cleared": p["rights_state"] in CLEARED, "ai_generated": p["ai_generated"],
                          "path": str(LIB / p["file"]), "description": p.get("description"),
                          "teaching_purpose": p.get("teaching_purpose"), "credit": p.get("credit"),
                          "licence": p.get("licence"), "page_url": p.get("page_url"),
                          "visually_verified": p.get("visually_verified"), "caption_caveat": p.get("caption_caveat"),
                          "px": p.get("px"), "courses": p.get("courses", []), "topics": p.get("topics", []),
                          "match": p.get("_match")} for p in pics],
            "documents": [{"title": d["title"], "type": d["doc_type"], "edition": d.get("edition"),
                           "distribution": d["rights_state"], "path": str(LIB / d["file"]),
                           "origin": d.get("origin")} for d in dmatch],
            "passages": [{"where": S.where(c), "kb": c["_kb"], "chunk_id": c.get("chunk_id"),
                          "original_pdf": str(LIB / doc_of[c["doc_id"]]["file"]) if c.get("doc_id") in doc_of else None,
                          "snippet": snippet(c.get("text"), pat)} for _, c in hits],
        }, ensure_ascii=False, indent=1))
        return

    L = [f"# {C.NAME} - {a.query}", ""]
    if phrases[1:]:
        L += [f"Also searched as: {', '.join(phrases[1:])}", ""]
    L += ["## Topics", ""]
    for t in topics:
        mods = "; ".join(f"{c}: {', '.join(m)}" for c, m in t.get("courses", {}).items() if m)
        L.append(f"- **{t['id']}** {t['title']} - {mods or 'no module yet'}")
    L += ["" if topics else "- none matched", "", "## Facts (knowledge/FACTS.md)", ""]
    for _, h, c in facts:
        flag = " **[CONFLICT - not settled]**" if any("CONFLICT" in x for x in c) else ""
        L.append(f"- {' | '.join(x for x in c if x)[:420]}{flag}  _(section: {h[:60]})_")
    if not facts:
        L.append("- none")
    L += ["", "## Glossary (knowledge/GLOSSARY.md)", ""]
    L += [f"- **{c[0]}**: {c[3] if len(c) > 3 else ''} _(source: {c[4] if len(c) > 4 else '-'})_" for _, _, c in gloss] or ["- none"]
    L += ["", "## Regulations held (knowledge/REGULATIONS.md)", ""]
    L += [f"- {' | '.join(x for x in c if x)[:300]}" for _, _, c in regs] or ["- none matched"]
    if inbox:
        L += ["", "## Inbox (knowledge/INBOX.md - added by course sessions; NEW = not reviewed, check the source)", ""]
        L += [f"- {' | '.join(x for x in c if x)[:300]}" for _, _, c in inbox]
    L += ["", "## Pictures (cleared first; `python tools/use_asset.py <id> <module folder>`)", ""]
    for p in pics:
        tag = "cleared" if p["rights_state"] in CLEARED else "NOT cleared"
        ai = ", AI" if p["ai_generated"] else ""
        L.append(f"- `{p['id']}` - {p['kind']}{ai} - {p['rights_state']} ({tag}) - {', '.join(p.get('courses', []))} - "
                 f"{str(p.get('description') or '')[:140]}\n  `{LIB / p['file']}`")
    if not pics:
        L.append("- none in the library - next: level 3 (visual-sourcer) or a real photo at Novikontas")
    L += ["", "## Reference documents (distribution: SHARE / FREE_DOWNLOAD / INSTRUCTOR_ONLY / CHECK)", ""]
    for d in dmatch:
        L.append(f"- **{d['title']}** - {d['doc_type']}{', ' + d['edition'] if d.get('edition') else ''} - "
                 f"{d['rights_state']}\n  `{LIB / d['file']}`")
    if not dmatch:
        L.append("- none held as a file")
    L += ["", f"## Source passages ({n} pieces searched; quote only with file + page)", ""]
    if on("passages") and not n:
        L.append(f"- {C.kb_hint()}")
    for i, (s, c) in enumerate(hits, 1):
        d = doc_of.get(c.get("doc_id"))
        L += [f"{i}. **{S.where(c)}** [{c['_kb']}]" + (" - original PDF in the library" if d else ""),
              f"   {snippet(c.get('text'), pat)}"]
    L += ["", f"More passages: `python tools/search.py \"{a.query}\" --top 20 --out retrieval/<name>.md`"]
    text = "\n".join(L)
    if a.out:
        out = Path(a.out) if Path(a.out).is_absolute() else LIB / a.out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
