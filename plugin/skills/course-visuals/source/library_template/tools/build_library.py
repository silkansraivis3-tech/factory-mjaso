"""Build this library from the courses, documents and knowledge bases in library_config.json.

    python tools/build_library.py                                  # harvest, copy new assets, write indexes + catalog
    python tools/build_library.py --kb-builder <kb_build.py>       # ... and make documents/ searchable
    python tools/build_library.py --dry-run                        # report only, copy and write nothing

What it does
  0. Index   - with the factory's knowledge-base builder (--kb-builder, or the env var
               NOVIKONTAS_KB_BUILDER; subject_library.py passes it), the library's own documents/ become
               a searchable KNOWLEDGE_BASE beside them. Without it the library works the same, and says
               its documents are not searchable yet.
  1. Assets  - reads every _photo_meta.json / _figure_meta.json / _sim_meta.json in every course
               module, joins identical files (same sha256) into one library asset, copies it into
               assets/<kind>/, tags it with topics from knowledge/topics.json, normalises the
               provenance (licence, credit, rights state) and records every place it is used.
  2. Sources - reads SOURCE_MANIFEST.json of every knowledge base, joins identical source files
               (same sha256) across KBs, and tags each source with the topics its text covers.
  3. Writes  - assets/ASSETS.json, knowledge/SOURCES.json, documents/DOCUMENTS.json, LIBRARY_INDEX.md,
               CHECKS.md, catalog.html, courses/<course>.md.

Nothing in a course or a knowledge base is changed. Re-running is safe: an asset already in the
library is not copied again, and records are rebuilt from the course metadata every time.
"""
import argparse
import collections
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import libconfig as C  # noqa: E402

LIB = C.LIB
META_KINDS = {"_photo_meta.json": "photo", "_figure_meta.json": "figure", "_sim_meta.json": "sim"}
KIND_DIR = {"photo": "photos", "figure": "figures", "sim": "sim", "render": "renders"}
INDEXED = (".pdf", ".docx", ".pptx", ".doc", ".ppt")
OWN_KB = LIB / "KNOWLEDGE_BASE"

try:
    from PIL import Image
except ImportError:  # dimensions are optional
    Image = None


_SHA_CACHE_FILE = LIB / ".cache" / "sha256.json"
_SHA_CACHE = None


def sha256(p):
    """sha256 of a file, cached by path + size + modification time (re-reading through Drive is slow)."""
    global _SHA_CACHE
    if _SHA_CACHE is None:
        try:
            _SHA_CACHE = json.loads(_SHA_CACHE_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _SHA_CACHE = {}
    st = Path(p).stat()
    key = f"{Path(p).resolve()}|{st.st_size}|{int(st.st_mtime)}"
    if key in _SHA_CACHE:
        return _SHA_CACHE[key]
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    _SHA_CACHE[key] = h.hexdigest()
    return _SHA_CACHE[key]


def save_sha_cache():
    if _SHA_CACHE:
        _SHA_CACHE_FILE.parent.mkdir(exist_ok=True)
        _SHA_CACHE_FILE.write_text(json.dumps(_SHA_CACHE), encoding="utf-8")


def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def text_of(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return " ".join(text_of(x) for x in v)
    if isinstance(v, dict):
        return " ".join(text_of(x) for x in v.values())
    return str(v)


def first(meta, *keys):
    for k in keys:
        v = meta.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


# ---------------------------------------------------------------- the library's own documents, searchable

def index_documents(builder, dry_run):
    """Make documents/ a searchable knowledge base with the factory's kb_build.py. Returns one plain line."""
    docs = LIB / "documents"
    files = sorted(f for f in docs.rglob("*") if f.is_file() and f.suffix.lower() in INDEXED
                   and "_thumbs" not in f.parts) if docs.exists() else []
    if not files:
        return "documents: none held yet - nothing to make searchable"
    if not builder:
        return "documents: " + C.kb_hint()
    if not Path(builder).is_file():
        return f"documents: not searchable yet - no knowledge-base builder at {builder}"
    sig = hashlib.sha256("\n".join(f"{f.relative_to(docs).as_posix()}|{f.stat().st_size}|{int(f.stat().st_mtime)}"
                                   for f in files).encode()).hexdigest()
    mark = LIB / ".cache" / "kb_signature.txt"
    if (OWN_KB / "search_index").exists() and mark.exists() and mark.read_text(encoding="utf-8").strip() == sig:
        return f"documents: {len(files)} searchable (knowledge base up to date)"
    if dry_run:
        return f"documents: {len(files)} would be made searchable"
    r = subprocess.run([sys.executable, builder, str(docs), "--out", str(OWN_KB), "--no-images"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        return f"documents: not searchable yet - the builder stopped (exit {r.returncode}): {' / '.join(tail)}"
    mark.parent.mkdir(exist_ok=True)
    mark.write_text(sig, encoding="utf-8")
    return f"documents: {len(files)} made searchable in KNOWLEDGE_BASE/"


# ---------------------------------------------------------------- provenance normalising

def is_generated(name, meta):
    origin = text_of(meta.get("origin")).lower()
    if "generated" in origin or "render" in origin:
        return True
    if any(meta.get(k) for k in ("generated_by", "generator", "prompt", "generated")):
        return True
    return bool(re.search(r"(^|_)ai(_|\.|$)", name.lower()))


# copyrighted publishers whose figures stay classroom reference (library_config.json "publishers")
PUBLISHERS = tuple(C.CFG.get("publishers") or ("imo", "ics ", "ocimf", "iacs", "manual", "guide"))


def rights_state(meta, generated, folder_note=""):
    rs = meta.get("rights_state")
    if rs:
        return rs
    lic = text_of(first(meta, "licence", "license", "rights")).lower()
    origin = text_of(meta.get("origin")).lower()
    note = (folder_note or "").lower()
    src = text_of(first(meta, "source", "source_document", "extracted_from")).lower()
    if generated:
        return "GENERATED"
    if "pending" in note or "rights:" in note or "open question" in note:
        return "RIGHTS_REVIEW_REQUIRED"
    if not lic and any(p in src for p in PUBLISHERS):
        return "PUBLICATION_FIGURE"
    if "authored" in origin:
        return "PROJECT_OWNED"
    if "public domain" in lic or lic.strip() in ("pd", "cc0") or "cc0" in lic or "pd-" in lic:
        return "PUBLIC_DOMAIN"
    if "cc by" in lic or "cc-by" in lic or "creative commons" in lic:
        return "ATTRIBUTION_REQUIRED"
    if "pending" in lic or "question" in lic or "manufacturer" in lic or "review" in lic:
        return "RIGHTS_REVIEW_REQUIRED"
    if lic:
        return "SEE_LICENCE"
    return "UNKNOWN"


def completeness(meta):
    return sum(1 for v in meta.values() if v not in (None, "", [], {}))


def tag_topics(blob, topics):
    blob = blob.lower().replace("_", " ")
    return [t["id"] for t in topics if any(k in blob for k in t.get("keywords", []))]


def dhash(im, size=8):
    """Difference hash: the same picture saved at another size or quality gives (almost) the same hash."""
    g = im.convert("L").resize((size + 1, size))
    px = list(g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            bits = (bits << 1) | (px[row * (size + 1) + col] > px[row * (size + 1) + col + 1])
    return bits


def near_duplicates(assets, max_distance=6):
    hashed = [a for a in assets if a.get("_dhash") is not None]
    pairs = []
    for i, a in enumerate(hashed):
        for b in hashed[i + 1:]:
            d = bin(a["_dhash"] ^ b["_dhash"]).count("1")
            if d <= max_distance:
                pairs.append((a, b, d))
    return pairs


def clean_id(name):
    stem = Path(name).stem.lower()
    stem = re.sub(r"^m\d{2}_(s\d{2}_)?", "", stem)
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    return stem or "asset"


# ---------------------------------------------------------------- harvest assets

def harvest_assets(cfg, topics):
    found = collections.defaultdict(list)  # sha -> uses
    problems = []
    for course in cfg.get("courses", []):
        root = C.resolve(course.get("module_root"))
        if not root:
            continue
        if not root.exists():
            problems.append(f"course {course['id']}: module_root not found: {root}")
            continue
        for mod in sorted(root.glob(course.get("module_glob") or "*")):
            if not mod.is_dir():
                continue
            for meta_file in sorted(mod.rglob("_*_meta.json")):
                kind = META_KINDS.get(meta_file.name)
                if not kind:
                    continue
                try:
                    data = load_json(meta_file)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"{meta_file}: unreadable JSON ({e})")
                    continue
                folder_note = text_of(data.get("_note"))
                for name, meta in data.items():
                    if name.startswith("_") or not isinstance(meta, dict):
                        continue
                    f = meta_file.parent / name
                    if not f.exists():
                        problems.append(f"{course['id']} {mod.name}: '{name}' is in {meta_file.name} but the file is missing")
                        continue
                    found[sha256(f)].append({
                        "course": course["id"], "module": mod.name, "name": name, "kind": kind,
                        "path": str(f), "meta": meta, "folder_note": folder_note,
                    })
    return found, problems


def build_asset_records(found, topics, existing):
    by_sha_existing = {a["sha256"]: a for a in existing}
    taken = {a["id"] for a in existing}
    records = []
    for sha, uses in found.items():
        best = max(uses, key=lambda u: completeness(u["meta"]))
        m = best["meta"]
        generated = is_generated(best["name"], m)
        cgi = text_of(m.get("origin")).lower().startswith("cgi")
        kind = "render" if ((generated or cgi) and best["kind"] == "photo") else best["kind"]
        old = by_sha_existing.get(sha)
        if old:
            aid = old["id"]
        else:
            aid = base = clean_id(best["name"])
            n = 2
            while aid in taken:
                aid = f"{base}_{n}"
                n += 1
            taken.add(aid)
        ext = Path(best["name"]).suffix.lower()
        blob = " ".join([best["name"], text_of(m.get("description")), text_of(m.get("shows")),
                         text_of(m.get("teaching_purpose")), text_of(m.get("caption_in_source"))])
        rec = {
            "id": aid,
            "file": f"assets/{KIND_DIR[kind]}/{aid}{ext}",
            "kind": kind,
            "ai_generated": generated,
            "sha256": sha,
            "bytes": Path(best["path"]).stat().st_size,
            "topics": sorted(set(tag_topics(blob, topics)) | set(m.get("topics_hint") or [])),
            "description": first(m, "description", "shows", "caption_in_source"),
            "teaching_purpose": first(m, "teaching_purpose"),
            "shows": first(m, "shows"),
            "rights_state": rights_state(m, generated, best["folder_note"]),
            "licence": first(m, "licence", "license", "rights"),
            "licence_url": first(m, "licence_url", "license_url"),
            "credit": first(m, "credit", "author"),
            "author": first(m, "author"),
            "source": first(m, "source", "source_document", "extracted_from", "url_or_origin", "origin"),
            "page_url": first(m, "page_url", "url_or_origin"),
            "attribution_required": m.get("attribution_required"),
            "visually_verified": first(m, "visually_verified"),
            "caption_caveat": first(m, "caption_caveat"),
            "generated_by": first(m, "generated_by", "generator"),
            "folder_note": best["folder_note"] or None,
            "used_in": [{"course": u["course"], "module": u["module"], "name_in_course": u["name"],
                         "used_in": u["meta"].get("used_in"), "path": u["path"]} for u in uses],
            "courses": sorted({u["course"] for u in uses}),
            "_source_path": best["path"],
            "_full_meta": m,
        }
        if Image and ext in (".jpg", ".jpeg", ".png", ".webp"):
            try:
                with Image.open(best["path"]) as im:
                    rec["px"] = f"{im.width}x{im.height}"
                    rec["_dhash"] = dhash(im)
            except Exception:  # noqa: BLE001
                pass
        records.append(rec)
    order = {"photo": 0, "render": 1, "figure": 2, "sim": 3}
    records.sort(key=lambda r: (order.get(r["kind"], 9), r["id"]))
    return records


# ---------------------------------------------------------------- harvest sources

def harvest_sources(cfg, topics):
    by_sha = {}
    problems = []
    for kb in cfg.get("knowledge_bases", []):
        kbp = C.resolve(kb["path"])
        man = kbp / "SOURCE_MANIFEST.json"
        if not man.exists():
            if kbp != OWN_KB:
                problems.append(f"{kb['id']}: SOURCE_MANIFEST.json not found at {kbp}")
            continue
        manifest = load_json(man)
        moved = C.resolve(kb.get("moved_sources_path"))
        hits = collections.defaultdict(collections.Counter)
        idx = kbp / "search_index" / "chunks.jsonl"
        if idx.exists() and topics:
            with open(idx, encoding="utf-8") as f:
                for line in f:
                    try:
                        c = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    t = (c.get("text") or "").lower()
                    for top in topics:
                        n = sum(t.count(k) for k in top.get("keywords", []) if len(k) > 3)
                        if n:
                            hits[c.get("doc_id")][top["id"]] += n
        for s in manifest.get("sources", []):
            sha = s.get("sha256")
            if not sha:
                continue
            out = s.get("output_folder") or ""
            folder_name = Path(out).name
            if (kbp / out).exists():
                where, folder = "in KB", str(kbp / out)
            elif moved and (moved / folder_name).exists():
                where, folder = "moved", str(moved / folder_name)
            else:
                where, folder = "missing", None
            floor = max(8, 0.3 * (s.get("unit_count") or 0))
            top_topics = [t for t, n in hits[s.get("doc_id")].most_common(4) if n >= floor]
            title = Path(s.get("original_filename", "")).stem.lower().replace("_", " ")
            top_topics += [t["id"] for t in topics if t["id"] not in top_topics
                           and any(k in title for k in t.get("keywords", []) if len(k) > 3)]
            rec = by_sha.setdefault(sha, {
                "sha256": sha, "title": Path(s.get("original_filename", "")).stem,
                "original_filename": s.get("original_filename"), "units": s.get("unit_count"),
                "unit_kind": s.get("unit_kind"), "status": s.get("status"),
                "topics": top_topics, "copies": [],
            })
            for t in top_topics:
                if t not in rec["topics"]:
                    rec["topics"].append(t)
            rec["copies"].append({"kb": kb["id"], "doc_id": s.get("doc_id"),
                                  "source_path": s.get("source_path"), "where": where, "folder": folder})
    recs = sorted(by_sha.values(), key=lambda r: r["title"].lower())
    for r in recs:
        r["kbs"] = sorted({c["kb"] for c in r["copies"]})
    return recs, problems


# ---------------------------------------------------------------- harvest reference documents

DOC_EXT = (".pdf",)


def harvest_documents(cfg, sources, dry_run=False):
    """Original reference PDFs: one copy each in documents/<type>/, joined with the KB that holds the text."""
    facts_file = LIB / "documents" / "document_sources.json"
    nfc = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731 - letters can arrive decomposed from Drive
    known = {nfc(k): v for k, v in load_json(facts_file, {"documents": {}}).get("documents", {}).items()}
    by_sha = {s["sha256"]: s for s in sources}
    docs, problems, seen = [], [], {}
    try:
        import pymupdf
    except ImportError:
        pymupdf = None
    in_place_root = LIB / "documents"
    for root in [in_place_root] + [C.resolve(r) for r in cfg.get("document_roots", [])]:
        if not root.exists():
            problems.append(f"document root not found: {root}")
            continue
        for f in sorted(root.rglob("*")):
            if f.suffix.lower() not in DOC_EXT or not f.is_file() or "_thumbs" in f.parts:
                continue
            sha = sha256(f)
            if sha in seen:
                seen[sha]["also_at"].append(str(f))
                continue
            k = known.get(nfc(f.name), {})
            src = by_sha.get(sha)
            in_place = root == in_place_root
            dtype = k.get("type") or (f.parent.name if in_place else "unsorted")
            rec = {
                "id": "doc_" + clean_id(f.name),
                "kind": "document",
                "file": f.relative_to(LIB).as_posix() if in_place else f"documents/{dtype}/{f.name}",
                "thumb": f"documents/_thumbs/{sha[:12]}.png",
                "sha256": sha, "bytes": f.stat().st_size,
                "doc_type": dtype,
                "title": k.get("title") or f.stem,
                "description": k.get("title") or f.stem,
                "edition": k.get("edition"),
                "origin": k.get("origin_url") or k.get("origin") or "not recorded",
                "rights_state": k.get("distribution") or "CHECK",
                "note": k.get("note"),
                "pages": (src or {}).get("units"),
                "in_kbs": (src or {}).get("kbs", []),
                "topics": (src or {}).get("topics", []),
                "courses": [], "ai_generated": False,
                "_source_path": str(f), "also_at": [],
                "_described": bool(k),
            }
            if pymupdf and not dry_run:
                thumb = LIB / rec["thumb"]
                try:
                    if not thumb.exists():
                        thumb.parent.mkdir(parents=True, exist_ok=True)
                        with pymupdf.open(f) as d:
                            rec["pages"] = rec["pages"] or d.page_count
                            page = d[0]
                            page.get_pixmap(matrix=pymupdf.Matrix(300 / page.rect.width, 300 / page.rect.width)).save(thumb)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"{f.name}: no thumbnail ({e})")
            if not src:
                problems.append(f"{f.name}: not in any knowledge base - its text is not searchable yet")
            seen[sha] = rec
            docs.append(rec)
            if src:
                src["library_document"] = rec["file"]
    docs.sort(key=lambda d: (d["doc_type"], d["title"].lower()))
    return docs, problems


# ---------------------------------------------------------------- outputs

RIGHTS_HELP = {
    "PUBLICATION_FIGURE": "figure or photo taken from a copyrighted publication we hold - "
                          "fine for internal classroom use; ask the owner before it ships on the tablets",
    "RIGHTS_REVIEW_REQUIRED": "the course itself logged an open rights question",
    "UNKNOWN": "no licence or source recorded - find where it came from",
    "SEE_LICENCE": "licence text recorded but not recognised - read it",
}


def taught(cfg):
    return [c for c in cfg.get("courses", []) if c.get("kind") != "import"]


def write_index(cfg, topics, assets, sources, problems, docs=()):
    today = date.today().isoformat()
    courses = taught(cfg)
    L = [f"# {C.NAME} - index", "",
         f"Built {today} by `tools/build_library.py`. Do not edit by hand - edit the courses or "
         "`library_config.json` / `knowledge/topics.json` and rebuild.", "",
         f"**{len(assets)} assets** ({sum(a['kind']=='photo' for a in assets)} real photos, "
         f"{sum(a['kind']=='render' for a in assets)} AI renders, {sum(a['kind']=='figure' for a in assets)} figures, "
         f"{sum(a['kind']=='sim' for a in assets)} simulator screens) - "
         f"**{len(sources)} unique source documents** across {len(cfg.get('knowledge_bases', []))} knowledge bases.", "",
         "Open `catalog.html` to browse the pictures.", "",
         "## Courses", "", "| Course | Owner | Status | Assets used |", "|---|---|---|---|"]
    for c in cfg.get("courses", []):
        n = sum(c["id"] in a["courses"] for a in assets)
        L.append(f"| {c['title']} | {c.get('owner', '')} | {c.get('status', '')} | {n} |")
    if not cfg.get("courses"):
        L.append("| none registered yet - `tools/contribute.py register-course` | | | |")
    shared = [a for a in assets if len(a["courses"]) > 1]
    L += ["", f"Assets used by more than one course: **{len(shared)}**", "", "## Topics", ""]
    if topics:
        L += ["| Topic | " + " | ".join(c["id"] for c in courses) + " | Assets | Sources |",
              "|---|" + "---|" * len(courses) + "---|---|"]
        for t in topics:
            na = sum(t["id"] in a["topics"] for a in assets)
            ns = sum(t["id"] in s["topics"] for s in sources)
            cols = [", ".join(t.get("courses", {}).get(c["id"], [])) or "-" for c in courses]
            L.append(f"| **{t['id']}** {t['title']} | {' | '.join(cols)}{' | ' if cols else ''}{na} | {ns} |")
    else:
        L.append("- none yet - add them to `knowledge/topics.json`")
    L += ["", f"## Reference documents held ({len(docs)} PDFs, `documents/`)", "",
          "Distribution: SHARE = may go to trainees; FREE_DOWNLOAD = free from the publisher, fine in class; "
          "INSTRUCTOR_ONLY = licensed copy; CHECK = a person must decide. Facts kept in `documents/document_sources.json`.", "",
          "| Document | Type | Edition | Pages | Distribution | Text in KB | File |", "|---|---|---|---|---|---|---|"]
    for d in docs:
        L.append(f"| {d['title']} | {d['doc_type']} | {d.get('edition') or ''} | {d.get('pages') or ''} | "
                 f"{d['rights_state']} | {', '.join(d['in_kbs']) or 'no'} | `{d['file']}` |")
    L += ["", "## Source documents", "", "Same sha256 = same file; a document in several KBs is listed once.", "",
          "| Document | Units | In KBs | Where | Topics |", "|---|---|---|---|---|"]
    for s in sources:
        where = "; ".join(sorted({c["where"] for c in s["copies"]}))
        L.append(f"| {s['title']} | {s['units'] or ''} {s['unit_kind'] or ''} | {', '.join(s['kbs'])} | {where} | {' '.join(s['topics'])} |")
    L += ["", "## Assets by topic", ""]
    for t in topics:
        items = [a for a in assets if t["id"] in a["topics"]]
        if not items:
            continue
        L += [f"### {t['id']} {t['title']}", ""]
        for a in items:
            flag = " (AI)" if a["ai_generated"] else ""
            L.append(f"- `{a['id']}` - {a['kind']}{flag} - {a['rights_state']} - {', '.join(a['courses'])} - "
                     f"{html.unescape(text_of(a['description']))[:110]}")
        L.append("")
    untagged = [a for a in assets if not a["topics"]]
    if untagged:
        L += ["### Not tagged yet", ""] + [f"- `{a['id']}` - {text_of(a['description'])[:110]}" for a in untagged] + [""]
    (LIB / "LIBRARY_INDEX.md").write_text("\n".join(L), encoding="utf-8")

    Ck = [f"# {C.NAME} - checks - {today}", "", "Things a person should look at. Rebuild to refresh.", ""]
    review = [a for a in assets if a["rights_state"] not in C.SHIP_STATES]
    Ck += [f"## Rights to clear ({len(review)})", "",
           "Not public domain / CC / owner-cleared / our own. Do not publish to the tablets until cleared.", ""]
    for state in sorted({a["rights_state"] for a in review}):
        group = [a for a in review if a["rights_state"] == state]
        Ck += [f"### {state} ({len(group)}) - {RIGHTS_HELP.get(state, '')}", ""]
        Ck += [f"- `{a['id']}` - {', '.join(a['courses'])} - {text_of(a['source'])[:90] or 'no source recorded'}" for a in group]
        Ck.append("")
    ai = [a for a in assets if a["ai_generated"]]
    Ck += ["", f"## AI-generated pictures ({len(ai)})", "",
           "Rule: never an AI image of equipment a trainee must recognise - replace with a real photo "
           "(Novikontas or credited free licence) where the picture shows real equipment.", ""]
    Ck += [f"- `{a['id']}` - {', '.join(a['courses'])} - {text_of(a['description'])[:110]}" for a in ai]
    nover = [a for a in assets if not a["visually_verified"]]
    Ck += ["", f"## Not visually verified ({len(nover)})", ""] + [f"- `{a['id']}`" for a in nover]
    names = collections.defaultdict(set)
    for a in assets:
        for u in a["used_in"]:
            names[(u["course"], u["name_in_course"])].add(a["id"])
    Ck += ["", "## Same course file name, different picture", ""]
    Ck += [f"- {c} `{n}` -> {', '.join(sorted(ids))}" for (c, n), ids in names.items() if len(ids) > 1] or ["- none"]
    pairs = near_duplicates(assets)
    Ck += ["", f"## Probably the same picture, different file ({len(pairs)})", "",
           "Same image at another size or crop. Keep the better one in the library and point both courses at it.", ""]
    Ck += [f"- `{a['id']}` ({a.get('px')}, {', '.join(a['courses'])}) ~ `{b['id']}` ({b.get('px')}, {', '.join(b['courses'])}) - distance {d}"
           for a, b, d in pairs] or ["- none"]
    bad_svg = []
    for a in assets:
        if a["file"].endswith(".svg"):
            try:
                ET.parse(a["_source_path"])
            except ET.ParseError as e:
                bad_svg.append(f"- `{a['id']}` ({a['used_in'][0]['path']}) - {e}")
    Ck += ["", f"## SVG files that are not valid XML ({len(bad_svg)})", ""] + (bad_svg or ["- none"])
    check = [d for d in docs if d["rights_state"] == "CHECK"]
    Ck += ["", f"## Documents whose distribution must be decided ({len(check)})", "",
           "Set `distribution` in documents/document_sources.json.", ""]
    Ck += [f"- {d['title']} (`{d['file']}`) - origin: {d['origin']}" for d in check] or ["- none"]
    undesc = [d for d in docs if not d["_described"]]
    Ck += ["", f"## Documents not described yet ({len(undesc)})", ""] + [f"- `{d['file']}`" for d in undesc]
    missing = [s for s in sources if any(c["where"] == "missing" for c in s["copies"])]
    Ck += ["", f"## Source folders missing ({len(missing)})", ""] + [f"- {s['title']} ({', '.join(s['kbs'])})" for s in missing]
    Ck += ["", f"## Harvest problems ({len(problems)})", ""] + [f"- {p}" for p in problems]
    (LIB / "CHECKS.md").write_text("\n".join(Ck), encoding="utf-8")


def write_course_pages(cfg, topics, assets, sources):
    """One page per course: per topic it teaches, what it uses and what the library offers it from elsewhere."""
    out = LIB / "courses"
    out.mkdir(exist_ok=True)
    for c in taught(cfg):
        cid = c["id"]
        own = [a for a in assets if cid in a["courses"]]
        L = [f"# {c['title']}", "", f"Owner: {c.get('owner', '')} - status: {c.get('status', '')}", "",
             f"Uses **{len(own)}** library assets. Built {date.today().isoformat()} by build_library.py.", "",
             "Per topic: what this course already shows, and what the library has from the other courses "
             "(copy one in with `tools/use_asset.py <id> <module folder>`).", ""]
        for t in topics:
            mods = t.get("courses", {}).get(cid, [])
            if not mods and c.get("module_root"):
                continue
            mine = [a for a in own if t["id"] in a["topics"]]
            other = [a for a in assets if t["id"] in a["topics"] and cid not in a["courses"]]
            srcs = [s for s in sources if t["id"] in s["topics"] and c.get("kb") not in s["kbs"]]
            L += [f"## {t['id']} {t['title']}", "", f"Modules: {', '.join(mods) or 'not planned yet'}", ""]
            L.append(f"- Uses ({len(mine)}): " + (", ".join(f"`{a['id']}`" for a in mine) or "-"))
            L.append(f"- Available from other courses ({len(other)}): " +
                     (", ".join(f"`{a['id']}`{' (AI)' if a['ai_generated'] else ''}" for a in other) or "-"))
            L.append(f"- Sources on this topic not in this course's KB ({len(srcs)}): " +
                     ("; ".join(s["title"] for s in srcs[:12]) + (" ..." if len(srcs) > 12 else "") if srcs else "-"))
            L.append("")
        (out / f"{cid}.md").write_text("\n".join(L), encoding="utf-8")


def write_catalog(cfg, topics, assets, docs=()):
    tpl = (LIB / "tools" / "catalog_template.html").read_text(encoding="utf-8")
    data = {
        "built": date.today().isoformat(),
        "courses": [{"id": c["id"], "title": c["title"]} for c in cfg.get("courses", [])],
        "topics": [{"id": t["id"], "title": t["title"]} for t in topics],
        "assets": [{k: v for k, v in a.items() if not k.startswith("_") and k != "used_in"} |
                   {"used_in": [{k: u[k] for k in ("course", "module", "name_in_course", "used_in")} for u in a["used_in"]]}
                   for a in assets] +
                  [{k: v for k, v in d.items() if not k.startswith("_")} | {"used_in": []} for d in docs],
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = tpl.replace("/*__DATA__*/null", payload).replace("__LIBRARY_NAME__", html.escape(C.NAME))
    (LIB / "catalog.html").write_text(page, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--kb-builder", default=os.environ.get("NOVIKONTAS_KB_BUILDER"),
                    help="the factory's kb/builder/kb_build.py - makes documents/ searchable")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = C.config()
    topics = load_json(LIB / "knowledge" / "topics.json", {"topics": []}).get("topics", [])
    reg = LIB / "assets" / "ASSETS.json"
    existing = load_json(reg, {"assets": []}).get("assets", [])

    print(index_documents(args.kb_builder, args.dry_run))
    found, problems = harvest_assets(cfg, topics)
    assets = build_asset_records(found, topics, existing)
    sources, sproblems = harvest_sources(cfg, topics)
    problems += sproblems
    docs, dproblems = harvest_documents(cfg, sources, args.dry_run)
    problems += dproblems
    save_sha_cache()
    for d in docs:
        dest = LIB / d["file"]
        if Path(d["_source_path"]) == dest:
            continue  # already in place
        if not args.dry_run and (not dest.exists() or dest.stat().st_size != d["bytes"]):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d["_source_path"], dest)
    print(f"documents: {len(docs)} reference PDFs; "
          f"{sum(d['rights_state'] == 'SHARE' for d in docs)} shareable, "
          f"{sum(d['rights_state'] == 'FREE_DOWNLOAD' for d in docs)} free downloads, "
          f"{sum(d['rights_state'] == 'INSTRUCTOR_ONLY' for d in docs)} instructor only, "
          f"{sum(d['rights_state'] == 'CHECK' for d in docs)} to check")

    copied = 0
    for a in assets:
        dest = LIB / a["file"]
        if not dest.exists() or sha256(dest) != a["sha256"]:
            copied += 1
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(a["_source_path"], dest)
    print(f"assets: {len(assets)} unique from {sum(len(v) for v in found.values())} course uses; "
          f"{copied} {'would be ' if args.dry_run else ''}copied; "
          f"{sum(len(a['courses']) > 1 for a in assets)} shared by more than one course")
    print(f"sources: {len(sources)} unique documents; {sum(len(s['kbs']) > 1 for s in sources)} in more than one KB")
    print(f"near-duplicate pictures: {len(near_duplicates(assets))}; problems: {len(problems)}")
    if args.dry_run:
        return 0
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps({"built": date.today().isoformat(),
                               "assets": [{k: v for k, v in a.items() if k not in ("_source_path", "_dhash")} for a in assets]},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    (LIB / "knowledge" / "SOURCES.json").write_text(
        json.dumps({"built": date.today().isoformat(), "sources": sources}, ensure_ascii=False, indent=1), encoding="utf-8")
    (LIB / "documents" / "DOCUMENTS.json").write_text(
        json.dumps({"built": date.today().isoformat(), "distribution_states":
                    load_json(LIB / "documents" / "document_sources.json", {}).get("distribution_states", {}),
                    "documents": [{k: v for k, v in d.items() if not k.startswith("_")} for d in docs]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    write_index(cfg, topics, assets, sources, problems, docs)
    write_catalog(cfg, topics, assets, docs)
    write_course_pages(cfg, topics, assets, sources)
    print("wrote assets/ASSETS.json, knowledge/SOURCES.json, documents/DOCUMENTS.json, LIBRARY_INDEX.md, CHECKS.md, "
          "catalog.html, courses/*.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
