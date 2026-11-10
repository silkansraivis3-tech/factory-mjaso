"""Search every knowledge base of this library at once and write a retrieval pack.

    python tools/search.py "<subject in plain words>"
    python tools/search.py "<subject>" --top 15
    python tools/search.py --topic T09                 # the topic's keywords from knowledge/topics.json
    python tools/search.py "<subject>" --kb library-documents --out retrieval/<name>.md
    python tools/search.py "<abbreviation>" --no-expand   # exactly these words, no synonyms

Reads the search_index/chunks.jsonl of every knowledge base in library_config.json (the library's own
documents/ are made searchable by tools/build_library.py with the factory's kb_build.py). A document
that sits in more than one KB (same sha256) is searched once, and the same passage found in two
editions or copies of a book is shown once. Synonyms come from knowledge/GLOSSARY.md and
knowledge/synonyms.json. Every hit carries its file and page, so a quote can be traced. For facts,
glossary, pictures and passages in one go, use tools/find.py.
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import libconfig as C  # noqa: E402

LIB = C.LIB
WORD = re.compile(r"[a-z0-9][a-z0-9\-\.%]*")
_CACHE = {}
# words too common on this subject to stand for a whole glossary term (library_config.json "generic_words")
GENERIC = set(C.CFG.get("generic_words") or ["ship", "ships", "vessel", "system", "safety", "code"])


def words(s):
    return [w.strip(".-") for w in WORD.findall(s.lower()) if w.strip(".-")]


# ---------------------------------------------------------------- synonyms

def synonym_groups():
    if "groups" in _CACHE:
        return _CACHE["groups"]
    groups = []
    syn = LIB / "knowledge" / "synonyms.json"
    if syn.exists():
        groups += [set(g) for g in json.loads(syn.read_text(encoding="utf-8")).get("groups", [])]
    glo = LIB / "knowledge" / "GLOSSARY.md"
    if glo.exists():
        for line in glo.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| ") or line.startswith("| Term") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            term, meaning = cells[0].replace("*", ""), cells[3]
            names = set()
            for part in re.split(r"\s+/\s+|[()]", term):
                part = part.strip(" .,'\"").lower()
                if 1 < len(part) <= 40:
                    names.add(part)
            head = meaning.split(":")[0].strip().lower() if ":" in meaning else ""
            if head and len(head.split()) <= 6:
                names.add(re.sub(r"\s*\([^)]*\)", "", head))
                names.add(re.sub(r"(\w+) \((\w+)\)", r"\2", head))
            names = {n for n in names if n not in GENERIC and "sense" not in n and "(" not in n}
            if len(names) > 1:
                groups.append(names)
    _CACHE["groups"] = groups
    return groups


def expand(query):
    """Phrases to look for: the query itself plus every synonym of a term it contains."""
    q = " " + " ".join(words(query)) + " "
    phrases = [query.lower().strip()]
    for g in synonym_groups():
        if any(f" {p} " in q for p in g if p):
            phrases += [p for p in g if p not in phrases]
    return phrases


# ---------------------------------------------------------------- index

def load_chunks(cfg, only_kb=None, quiet=False):
    key = ("chunks", only_kb)
    if key in _CACHE:
        return _CACHE[key]
    seen_sha = {}
    chunks = []
    for kb in cfg.get("knowledge_bases", []):
        if only_kb and kb["id"] != only_kb:
            continue
        kbp = C.resolve(kb["path"])
        man = kbp / "SOURCE_MANIFEST.json"
        doc_sha = {}
        if man.exists():
            for s in json.loads(man.read_text(encoding="utf-8")).get("sources", []):
                doc_sha[s.get("doc_id")] = s.get("sha256")
        idx = kbp / "search_index" / "chunks.jsonl"
        if not idx.exists():
            if not quiet:
                print(f"! {kb['id']}: no search index yet at {idx} - {C.kb_hint()}", file=sys.stderr)
            continue
        with open(idx, encoding="utf-8") as f:
            for line in f:
                try:
                    c = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if c.get("navigational"):
                    continue
                sha = doc_sha.get(c.get("doc_id"))
                owner = seen_sha.setdefault(sha, kb["id"]) if sha else kb["id"]
                if owner != kb["id"]:
                    continue  # same document already loaded from an earlier KB
                c["_kb"] = kb["id"]
                c["_tok"] = Counter(words(c.get("text", "")))
                chunks.append(c)
    df = Counter()
    for c in chunks:
        df.update(c["_tok"].keys())
    avg = sum(sum(c["_tok"].values()) for c in chunks) / max(len(chunks), 1)
    _CACHE[key] = (chunks, df, avg)
    return _CACHE[key]


def score(index, phrases):
    chunks, df, avg = index
    n = len(chunks)
    terms = list(dict.fromkeys(w for p in phrases for w in words(p)))
    first = set(words(phrases[0]))
    out = []
    for c in chunks:
        t = c["_tok"]
        length = sum(t.values()) or 1
        s = 0.0
        for w in terms:
            if t[w]:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                weight = 1.0 if w in first else 0.6  # the asker's own words count more than synonyms
                s += weight * idf * t[w] * 2.2 / (t[w] + 1.2 * (0.25 + 0.75 * length / avg))
        text = c.get("text", "").lower()
        s += sum(3.0 for p in phrases if " " in p and p in text)
        if s > 0:
            out.append((s, c))
    out.sort(key=lambda x: -x[0])
    return out


def dedupe(hits, top):
    """Drop the same passage found again in another edition or copy of a book."""
    seen, out = set(), []
    for s, c in hits:
        sig = hashlib.md5(" ".join(words(c.get("text", "")))[:600].encode()).hexdigest()
        page = (c.get("source_filename"), c.get("page_start"))
        if sig in seen or page in seen:
            continue
        seen.update((sig, page))
        out.append((s, c))
        if len(out) >= top:
            break
    return out


def where(c):
    pages = c.get("page_start")
    if c.get("page_end") and c.get("page_end") != pages:
        pages = f"{pages}-{c['page_end']}"
    return f"{c.get('source_filename')} - {c.get('unit_kind', 'page')} {pages}"


def search(query, top=10, kb=None, no_expand=False, quiet=False):
    phrases = [query.lower()] if no_expand else expand(query)
    index = load_chunks(C.config(), kb, quiet)
    return phrases, dedupe(score(index, phrases), top), len(index[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--topic", help="topic id from knowledge/topics.json, e.g. T09")
    ap.add_argument("--kb", help="search one KB only (id from library_config.json)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", help="write a retrieval pack (markdown) to this path")
    ap.add_argument("--no-expand", action="store_true", help="no synonyms")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    query = args.query
    if args.topic:
        tp = LIB / "knowledge" / "topics.json"
        topics = {t["id"]: t for t in json.loads(tp.read_text(encoding="utf-8")).get("topics", [])} if tp.exists() else {}
        t = topics.get(args.topic.upper())
        if not t:
            sys.exit(f"unknown topic {args.topic}")
        query = (query + " " + " ".join(t["keywords"])).strip()
    if not query:
        sys.exit("give a query or --topic")
    phrases, hits, n = search(query, args.top, args.kb, args.no_expand or bool(args.topic))
    if not n:
        print(C.kb_hint())

    lines = [f"# {C.NAME} - retrieval pack - {args.query or args.topic}", "",
             f"{datetime.now():%Y-%m-%d %H:%M} - {n} pieces searched; also searched as: "
             f"{', '.join(phrases[1:]) or '-'}. Quote only with the file and page given.", ""]
    for i, (s, c) in enumerate(hits, 1):
        head = " > ".join(c.get("heading_path") or [])
        lines += [f"## {i}. {where(c)}",
                  f"KB `{c['_kb']}` - chunk `{c.get('chunk_id')}` - score {s:.1f}" + (f" - {head}" if head else ""), "",
                  (c.get("text") or "").strip()[:1800], ""]
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = LIB / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {out} ({len(hits)} hits)")
    if len(phrases) > 1:
        print("also searched as:", ", ".join(phrases[1:]))
    for i, (s, c) in enumerate(hits, 1):
        print(f"{i:2}. [{c['_kb']}] {where(c)}  ({s:.1f})")


if __name__ == "__main__":
    main()
