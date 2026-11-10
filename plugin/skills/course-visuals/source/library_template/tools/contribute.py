"""Add what a course session found to this library, so every course on its subject gets it.

    python tools/contribute.py picture <file> --source "Wikimedia Commons" --page-url <url> --licence "CC BY-SA 4.0" \
        --rights-state ATTRIBUTION_REQUIRED --credit "J. Smith / Wikimedia Commons, CC BY-SA 4.0" \
        --description "what the picture literally shows" --teaching-purpose "what it is for" \
        --visually-verified "yes - <what was seen> <date>" --by "course-factory, <course> M03"
    python tools/contribute.py picture <course>/modules/module03/assets/img/m03_x.jpg    # reads its _photo_meta.json
    python tools/contribute.py document <file.pdf> --type regulation --title "..." --edition 2024 \
        --origin-url <publisher page> --distribution FREE_DOWNLOAD --by "..."
    python tools/contribute.py fact "<subject>" "<value with unit and conditions>" --source "<document, edition, page>"
    python tools/contribute.py term "<term>" "<meaning>" --source "<document, edition, section>"
    python tools/contribute.py regulation "<title>" "<edition / what it requires>" --source "<where it is published>"
    python tools/contribute.py register-course <id> --title "..." --owner "..." --module-root "<course>/modules" \
        --module-glob "module*" --map T05=M03,M04
    python tools/contribute.py withdraw picture <name in contributions/>  |  document <file name>  |  inbox <I001>

picture    The file and its provenance go into contributions/img|fig|sim with a _photo_meta.json /
           _figure_meta.json record; library_config.json lists contributions/ as an import, so the
           rebuild makes it a library asset (de-duplicated by sha256). A picture already in a course
           module the library harvests is not copied - the rebuild takes it from there.
           Refused without: source, rights_state, credit, description, teaching_purpose, visually_verified.
           An AI picture (--generator, or "generated" in its record) must be GENERATED and is flagged:
           never the picture of equipment a trainee must recognise (it is listed in CHECKS.md).
document   The PDF goes into documents/<type>/ and gets its entry in documents/document_sources.json,
           with its distribution (SHARE / FREE_DOWNLOAD / INSTRUCTOR_ONLY / CHECK). Refused without an
           origin and a distribution. Its text becomes searchable at the next rebuild with the factory's
           kb_build.py.
fact/term/ Appended to knowledge/INBOX.md with status NEW - never straight into FACTS.md, GLOSSARY.md
regulation or REGULATIONS.md. The reviewers (library_config.json "reviewers") review the inbox; find.py
           shows NEW rows as "not reviewed". A fact on a subject FACTS.md marks CONFLICT is taken, and
           its row says so.

The library is rebuilt after a picture, a document or a course; --no-rebuild when you add several,
then run tools/build_library.py once.
"""
import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import libconfig as C  # noqa: E402

LIB = C.LIB
CONFIG = LIB / "library_config.json"
CONTRIB = LIB / "contributions"
INBOX = LIB / "knowledge" / "INBOX.md"
DOC_FACTS = LIB / "documents" / "document_sources.json"

RIGHTS = set(C.SHIP_STATES) | {"RIGHTS_REVIEW_REQUIRED", "PUBLICATION_FIGURE", "UNKNOWN"}
SHIPPABLE = C.SHIP_STATES
DISTRIBUTION = {"SHARE", "FREE_DOWNLOAD", "INSTRUCTOR_ONLY", "CHECK"}
DOC_TYPES = set(C.CFG.get("document_types") or
                ["regulation", "sds", "manual", "guidance", "publication", "model_course", "programme", "course_material"])
PIC_EXT = {".jpg", ".jpeg", ".png", ".svg", ".webp", ".gif", ".mp4", ".webm"}
KIND_SUB = {"photo": ("img", "_photo_meta.json"), "render": ("img", "_photo_meta.json"),
            "figure": ("fig", "_figure_meta.json"), "sim": ("sim", "_sim_meta.json")}
REQUIRED = ("source", "rights_state", "credit", "description", "teaching_purpose", "visually_verified")
AI_FLAG = "AI-generated - never use it as the picture of equipment a trainee must recognise"
CONTRIB_COURSE = {
    "id": "contributions",
    "kind": "import",
    "title": "Contributions - pictures found or made while building a course (tools/contribute.py)",
    "owner": "the contributor (see each record's contributed_by)",
    "status": "added by course sessions - provenance in each record",
    "module_root": "{LIB}",
    "module_glob": "contributions",
}


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_raw(p):
    """The text with its own line endings - a hand-kept file keeps them when it is written back."""
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write_raw(p, text):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def nl(text):
    return "\r\n" if "\r\n" in text else "\n"


def save_json(p, data, indent=1):
    p = Path(p)
    n = nl(read_raw(p)) if p.exists() else "\n"
    write_raw(p, json.dumps(data, ensure_ascii=False, indent=indent).replace("\n", n) + n)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_") or "picture"


def library_assets():
    reg = LIB / "assets" / "ASSETS.json"
    return load_json(reg).get("assets", []) if reg.exists() else []


def rebuild(skip):
    if skip:
        print("not rebuilt (--no-rebuild) - run: python tools/build_library.py")
        return 0
    print("rebuilding the library ...")
    r = subprocess.run([sys.executable, str(LIB / "tools" / "build_library.py")], env=dict(os.environ))
    return r.returncode


def stop(msg):
    print(f"REFUSED - {msg}")
    sys.exit(2)


# ---------------------------------------------------------------- picture

def meta_beside(f):
    """The provenance record the course already wrote beside the file, if any."""
    for meta_name in ("_photo_meta.json", "_figure_meta.json", "_sim_meta.json"):
        p = f.parent / meta_name
        if p.exists():
            try:
                data = load_json(p)
            except ValueError:
                continue
            if isinstance(data.get(f.name), dict):
                return dict(data[f.name]), meta_name
    return {}, None


def registered_course_of(f):
    """The course in library_config.json whose modules hold this file (the build harvests it from there)."""
    cfg = load_json(CONFIG)
    rf = f.resolve()
    for c in cfg.get("courses", []):
        root = C.resolve(c.get("module_root"))
        if not root or c["id"] == "contributions" or c.get("kind") == "import" or not root.exists():
            continue
        for mod in root.glob(c.get("module_glob") or "*"):
            try:
                rf.relative_to(mod.resolve())
                return c["id"], mod.name
            except ValueError:
                continue
    return None, None


def ensure_contrib_course():
    cfg = load_json(CONFIG)
    if not any(c["id"] == "contributions" for c in cfg.get("courses", [])):
        cfg.setdefault("courses", []).append(CONTRIB_COURSE)
        save_json(CONFIG, cfg, indent=2)
        print("library_config.json: contributions/ added as an import")


def first(meta, *keys):
    for k in keys:
        v = meta.get(k)
        if v not in (None, "", [], {}):
            return v
    return None


def picture(a):
    f = Path(a.file)
    if not f.is_file():
        stop(f"no file {f}")
    if f.suffix.lower() not in PIC_EXT:
        stop(f"{f.suffix} does not render on the tablets - use one of {' '.join(sorted(PIC_EXT))}")
    meta, meta_name = meta_beside(f)
    sha = sha256(f)
    held = next((x for x in library_assets() if x["sha256"] == sha), None)
    if held:
        print(f"already in the library as `{held['id']}` ({held['rights_state']}) - nothing added")
        return 0
    course, module = registered_course_of(f)
    if course:  # the library never writes into a course: the build takes the course's own record
        if not meta_name:
            stop(f"{f.name} sits in {course} {module} but has no record in its _photo_meta.json / _figure_meta.json - "
                 "write it there first")
        gaps = [k for k in REQUIRED if not first(meta, k, *(("author",) if k == "credit" else ()))]
        print(f"{f.name} is in {course} {module}, which the library harvests - not copied; the rebuild takes it "
              "with its course record")
        if gaps:
            print(f"! its record has no {', '.join(gaps)} - complete it in the course's {meta_name}")
        if meta.get("generated") or first(meta, "generator", "generated_by", "prompt"):
            print(f"! {AI_FLAG}")
        return rebuild(a.no_rebuild)
    flags = {
        "source": a.source, "url_or_origin": a.page_url, "page_url": a.page_url, "author": a.author,
        "licence": a.licence, "licence_url": a.licence_url, "rights_state": a.rights_state, "credit": a.credit,
        "description": a.description, "teaching_purpose": a.teaching_purpose,
        "visually_verified": a.visually_verified, "caption_caveat": a.caption_caveat,
        "shows": a.shows or None, "topics_hint": a.topic or None, "generator": a.generator,
    }
    meta.update({k: v for k, v in flags.items() if v not in (None, "", [])})
    meta["source"] = first(meta, "source", "source_document", "url_or_origin", "origin")
    meta["credit"] = first(meta, "credit", "author")
    generated = bool(meta.get("generated") or first(meta, "generator", "generated_by", "prompt")) or \
        "generated" in str(meta.get("origin") or "").lower()
    if generated:
        meta["generated"] = True
        meta.setdefault("rights_state", "GENERATED")
        if not meta.get("credit"):
            meta["credit"] = f"AI-generated illustration ({first(meta, 'generator', 'generated_by') or 'model not recorded'})"
    rs = meta.get("rights_state")
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        stop(f"missing {', '.join(missing)} (from the flags or the {meta_name or '_photo_meta.json'} record beside the file). "
             "No picture enters the library without its source and rights.")
    if rs not in RIGHTS:
        stop(f"rights_state {rs!r} - use one of {', '.join(sorted(RIGHTS))}")
    if generated and rs != "GENERATED":
        stop(f"an AI picture is GENERATED, not {rs}")
    if not generated and rs == "GENERATED":
        stop("GENERATED is for AI pictures - give --generator <model>")
    if rs in ("ATTRIBUTION_REQUIRED", "PUBLIC_DOMAIN", "CLEARED") and not meta.get("licence"):
        stop(f"{rs} needs the licence (--licence, e.g. 'CC BY-SA 4.0', 'public domain')")
    vv = str(meta["visually_verified"]).strip()
    if vv.lower() in ("yes", "y", "true", "ok"):
        stop("visually_verified must say what was seen and when: 'yes - <what was seen> <date>' (or say it was not verified)")

    kind = a.kind or ("render" if generated else ("figure" if meta_name == "_figure_meta.json" or f.suffix.lower() == ".svg"
                                                  else "photo"))
    sub, out_meta = KIND_SUB[kind]
    folder = CONTRIB / sub
    folder.mkdir(parents=True, exist_ok=True)
    base, ext = slug(a.name and Path(a.name).stem or re.sub(r"^m\d{2}_(s\d{2}_)?", "", f.stem.lower())), f.suffix.lower()
    name, n = base + ext, 2
    while (folder / name).exists() and sha256(folder / name) != sha:  # never overwrite a different picture
        name, n = f"{base}_{n}{ext}", n + 1
    shutil.copy2(f, folder / name)
    meta_path = folder / out_meta
    data = load_json(meta_path) if meta_path.exists() else {
        "_note": "Added by tools/contribute.py - found or made while building a course. Each record names its source, "
                 "rights state and contributor."}
    record = {k: v for k, v in meta.items() if k not in ("library_id", "library_sha256")}
    record.update({"contributed_by": a.by or getpass.getuser(), "contributed": date.today().isoformat(),
                   "found_for": a.found_for or record.get("used_in") or "", "contributed_from": str(f)})
    if generated:
        record["ai_flag"] = AI_FLAG
    data[name] = record
    save_json(meta_path, data)
    ensure_contrib_course()
    print(f"added contributions/{sub}/{name} ({kind}, {rs}{', AI' if generated else ''}) to {C.NAME}")
    if rs not in SHIPPABLE:
        print(f"! {rs} - classroom reference only; listed in CHECKS.md 'Rights to clear' until cleared")
    if generated:
        print(f"! {AI_FLAG}")
    return rebuild(a.no_rebuild)


# ---------------------------------------------------------------- document

def write_doc_facts(data):
    """document_sources.json: the settings indented, then one document per line, so a person can keep it by hand."""
    docs = data.get("documents", {})
    head = {k: v for k, v in data.items() if k != "documents"}
    text = json.dumps(head, ensure_ascii=False, indent=2)[:-1].rstrip()
    rows = [f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}" for k, v in docs.items()]
    text += (",\n" if head else "\n") + '  "documents": {' + ("\n" + ",\n".join(rows) + "\n  }" if rows else "}") + "\n}\n"
    json.loads(text)  # never write a file the build cannot read
    write_raw(DOC_FACTS, text)


def document(a):
    f = Path(a.file)
    if not f.is_file() or f.suffix.lower() != ".pdf":
        stop(f"{f} is not a PDF file")
    if not (a.origin or a.origin_url):
        stop("say where it came from: --origin-url <publisher page> or --origin '<who gave it, how>'")
    if a.distribution not in DISTRIBUTION:
        stop(f"--distribution must be one of {', '.join(sorted(DISTRIBUTION))}")
    if a.type not in DOC_TYPES:
        stop(f"--type must be one of {', '.join(sorted(DOC_TYPES))}")
    nfc = lambda s: unicodedata.normalize("NFC", s)  # noqa: E731
    sha = sha256(f)
    reg = LIB / "documents" / "DOCUMENTS.json"
    held = next((d for d in (load_json(reg).get("documents", []) if reg.exists() else []) if d["sha256"] == sha), None)
    if held:
        print(f"already in the library: {held['title']} ({held['file']}, {held['rights_state']}) - nothing added")
        return 0
    data = load_json(DOC_FACTS) if DOC_FACTS.exists() else {"documents": {}}
    name = nfc(f.name)
    if name in {nfc(k) for k in data.get("documents", {})}:
        stop(f"a different document named '{name}' is already described - rename the file first")
    dest = LIB / "documents" / a.type / name
    if dest.exists():
        stop(f"{dest} exists and is a different file - rename the file first")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, dest)
    entry = {"type": a.type, "title": a.title, "edition": a.edition}
    entry.update({"origin_url": a.origin_url} if a.origin_url else {"origin": a.origin})
    entry.update({"distribution": a.distribution, "note": a.note,
                  "contributed_by": a.by or getpass.getuser(), "contributed": date.today().isoformat()})
    data.setdefault("documents", {})[name] = {k: v for k, v in entry.items() if v not in (None, "")}
    write_doc_facts(data)
    print(f"added documents/{a.type}/{name} ({a.distribution}) to {C.NAME}; described in documents/document_sources.json")
    if a.distribution == "INSTRUCTOR_ONLY":
        print("! INSTRUCTOR_ONLY - never to trainees or the tablets")
    return rebuild(a.no_rebuild)


# ---------------------------------------------------------------- facts, terms and regulations

INBOX_HEAD = f"""# Inbox - new facts, terms and regulations waiting for review

Added by course sessions with `python tools/contribute.py fact|term|regulation ...`. Nothing here is
settled: **NEW** = not reviewed. {C.REVIEWERS} check the source, then move the row into `FACTS.md` /
`GLOSSARY.md` / `REGULATIONS.md` and set ACCEPTED, or set REJECTED with the reason. Never quote a NEW
row on a slide without checking its source yourself. A row about a CONFLICT subject waits for
`OPEN_DECISIONS.md`.

| # | Kind | Status | Subject | Value / meaning | Source (document, edition, page) | Found for | Added | Note |
|---|---|---|---|---|---|---|---|---|
"""


def cell(s):
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "/").strip()


def inbox_rows():
    if not INBOX.exists():
        return []
    rows = []
    for line in INBOX.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*(I\d{3,})\s*\|", line)
        if m:
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def related_facts(subject):
    """FACTS.md rows on the same subject (whole words) as (row, conflict id or ''), conflicts first."""
    facts = LIB / "knowledge" / "FACTS.md"
    if not facts.exists():
        return []
    words = [w for w in re.findall(r"[a-z0-9]+", subject.lower()) if len(w) > 3]
    out, heading = [], ""
    for line in facts.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            heading = line.lower()
            continue
        if not line.startswith("| ") or line.startswith("|---") or re.match(r"\|\s*(Fact|#)\s*\|", line):
            continue
        low = line.lower()
        if words and all(re.search(rf"(?<![a-z0-9]){re.escape(w)}", low) for w in words):
            m = re.search(r"CONFLICT \((C\d+)\)", line) or ("conflict" in heading and re.match(r"\|\s*(C\d+)\s*\|", line))
            out.append((line, m.group(1) if m else ("?" if "CONFLICT" in line else "")))
    out.sort(key=lambda r: not r[1])
    return out


def inbox_add(kind, a):
    if not (a.source or "").strip():
        stop(f"a {kind} needs its source (document, edition, page or section) - "
             "a course-defined term: --source 'course-defined: <file>'")
    rows = inbox_rows()
    for r in rows:
        if len(r) > 5 and r[3].lower() == cell(a.subject).lower() and r[4].lower() == cell(a.value).lower() \
                and r[5].lower() == cell(a.source).lower():
            print(f"already in the inbox as {r[0]} ({r[2]}) - nothing added")
            return 0
    note = cell(a.note)
    if kind == "fact":
        rel = related_facts(a.subject)
        if rel and rel[0][1]:
            tag = rel[0][1]
            note = (f"FACTS.md marks this subject CONFLICT {tag} - not settled, see OPEN_DECISIONS.md. " + note).strip()
            print(f"! FACTS.md has this subject as CONFLICT {tag} - added for the reviewers, not settled "
                  "(OPEN_DECISIONS.md); do not pick a value on a slide")
        elif rel:
            note = ("FACTS.md already has a row on this subject - compare. " + note).strip()
            print("FACTS.md already has a row on this subject:\n  " + rel[0][0][:300])
    if kind in ("term", "regulation"):
        held = LIB / "knowledge" / ("GLOSSARY.md" if kind == "term" else "REGULATIONS.md")
        if held.exists() and re.search(rf"^\|\s*\**{re.escape(a.subject)}\**\s*[|(/]",
                                       held.read_text(encoding="utf-8"), re.I | re.M):
            note = (f"{held.name} already has it - compare. " + note).strip()
            print(f"{held.name} already has it - added for comparison")
    nid = f"I{max([int(r[0][1:]) for r in rows] or [0]) + 1:03d}"
    if not INBOX.exists():
        write_raw(INBOX, INBOX_HEAD)
    by = a.by or getpass.getuser()
    row = (f"| {nid} | {kind} | NEW | {cell(a.subject)} | {cell(a.value)} | {cell(a.source)} | "
           f"{cell(a.found_for) or '-'} ({cell(by)}) | {date.today().isoformat()} | {note} |")
    text = read_raw(INBOX)
    n = nl(text)
    write_raw(INBOX, text + ("" if text.endswith("\n") else n) + row + n)
    print(f"added {nid} to {C.NAME} knowledge/INBOX.md (NEW - for {C.REVIEWERS} to review)")
    return 0


# ---------------------------------------------------------------- a course

def register_course(a):
    cfg = load_json(CONFIG)
    cfg.setdefault("courses", [])
    c = next((x for x in cfg["courses"] if x["id"] == a.course_id), None)
    if a.module_root and not Path(a.module_root).exists():
        stop(f"module root not found: {a.module_root}")
    if not c:
        if not a.title:
            stop("a new course needs --title (and --owner)")
        c = {"id": a.course_id, "title": a.title, "owner": a.owner or "", "status": a.status or "being built",
             "module_root": None, "module_glob": None}
        cfg["courses"].insert(next((i for i, x in enumerate(cfg["courses"]) if x.get("kind") == "import"),
                                   len(cfg["courses"])), c)
    for k, v in (("title", a.title), ("owner", a.owner), ("status", a.status),
                 ("module_root", a.module_root and Path(a.module_root).as_posix()), ("module_glob", a.module_glob)):
        if v:
            c[k] = v
    if c.get("module_root") and not c.get("module_glob"):
        stop("give --module-glob too (e.g. 'module*' or 'Module_*')")
    save_json(CONFIG, cfg, indent=2)
    print(f"{C.NAME} library_config.json: {a.course_id} -> {c.get('module_root') or 'no modules yet'} ({c.get('module_glob')})")
    if a.map:
        tp = LIB / "knowledge" / "topics.json"
        data = load_json(tp)
        tmap = {t["id"]: t for t in data.get("topics", [])}
        for m in a.map:
            tid, _, mods = m.partition("=")
            if tid not in tmap:
                stop(f"no topic {tid} in knowledge/topics.json - add the topic there first")
            have = tmap[tid].setdefault("courses", {}).setdefault(a.course_id, [])
            have += [x.strip() for x in mods.split(",") if x.strip() and x.strip() not in have]
        save_json(tp, data, indent=2)
        print(f"knowledge/topics.json: {a.course_id} mapped on {len(a.map)} topic(s)")
    return rebuild(a.no_rebuild)


# ---------------------------------------------------------------- withdraw

def withdraw(a):
    if a.what == "inbox":
        if not INBOX.exists():
            stop("no inbox")
        lines = read_raw(INBOX).splitlines(keepends=True)
        keep = [l for l in lines if not re.match(rf"\|\s*{re.escape(a.name)}\s*\|\s*\w+\s*\|\s*NEW\s*\|", l)]
        if len(keep) == len(lines):
            stop(f"no NEW inbox row {a.name} (reviewed rows stay)")
        write_raw(INBOX, "".join(keep))
        print(f"removed {a.name} from knowledge/INBOX.md")
        return 0
    if a.what == "document":
        data = load_json(DOC_FACTS)
        e = data.get("documents", {}).get(a.name)
        if not e or "contributed" not in e:
            stop(f"'{a.name}' is not a contributed document - change document_sources.json by hand")
        f = LIB / "documents" / e["type"] / a.name
        if f.exists():
            thumb = LIB / "documents" / "_thumbs" / f"{sha256(f)[:12]}.png"
            f.unlink()
            if thumb.exists():
                thumb.unlink()
        del data["documents"][a.name]
        write_doc_facts(data)
        print(f"removed documents/{e['type']}/{a.name} and its entry")
        return rebuild(a.no_rebuild)
    for sub, meta_name in (("img", "_photo_meta.json"), ("fig", "_figure_meta.json"), ("sim", "_sim_meta.json")):
        f = CONTRIB / sub / a.name
        mp = CONTRIB / sub / meta_name
        if f.exists():
            sha = sha256(f)
            held = next((x for x in library_assets() if x["sha256"] == sha), None)
            f.unlink()
            if mp.exists():
                data = load_json(mp)
                data.pop(a.name, None)
                save_json(mp, data)
            print(f"removed contributions/{sub}/{a.name}")
            if held and all(u["course"] == "contributions" for u in held["used_in"]):
                copy = LIB / held["file"]
                if copy.exists():
                    copy.unlink()
                    print(f"removed the library copy {held['file']}")
            return rebuild(a.no_rebuild)
    stop(f"no contributions/img|fig|sim/{a.name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--by", help="who adds it (default: your user name), e.g. 'course-factory, <course> M03'")
    common.add_argument("--no-rebuild", action="store_true")

    p = sp.add_parser("picture", parents=[common])
    p.add_argument("file")
    p.add_argument("--kind", choices=sorted(KIND_SUB))
    p.add_argument("--name", help="file name in the library (default: from the file)")
    p.add_argument("--source", help="organisation / repository / 'NOVIKONTAS photo, <who>, <where>'")
    p.add_argument("--page-url")
    p.add_argument("--author")
    p.add_argument("--licence")
    p.add_argument("--licence-url")
    p.add_argument("--rights-state", help=", ".join(sorted(RIGHTS)))
    p.add_argument("--credit", help="the credit line shown with the picture")
    p.add_argument("--description", help="what the picture literally shows")
    p.add_argument("--teaching-purpose")
    p.add_argument("--visually-verified", help="'yes - <what was seen> <date>'")
    p.add_argument("--caption-caveat")
    p.add_argument("--shows", action="append", help="a thing it shows (repeatable)")
    p.add_argument("--topic", action="append", help="topic id from knowledge/topics.json (repeatable)")
    p.add_argument("--generator", help="the image model, for an AI picture")
    p.add_argument("--found-for", help="where it is used, e.g. '<course> M03 s05'")

    d = sp.add_parser("document", parents=[common])
    d.add_argument("file")
    d.add_argument("--type", required=True, help=", ".join(sorted(DOC_TYPES)))
    d.add_argument("--title", required=True)
    d.add_argument("--edition")
    d.add_argument("--origin-url")
    d.add_argument("--origin")
    d.add_argument("--distribution", required=True, help=", ".join(sorted(DISTRIBUTION)))
    d.add_argument("--note")

    for kind in ("fact", "term", "regulation"):
        f = sp.add_parser(kind, parents=[common])
        f.add_argument("subject", help="the fact's subject / the term / the regulation's title")
        f.add_argument("value", help="the value with its unit and conditions / the meaning / the edition and what it holds")
        f.add_argument("--source", required=True, help="document, edition, page or section")
        f.add_argument("--found-for")
        f.add_argument("--note")

    r = sp.add_parser("register-course", parents=[common])
    r.add_argument("course_id")
    r.add_argument("--title")
    r.add_argument("--owner")
    r.add_argument("--status")
    r.add_argument("--module-root")
    r.add_argument("--module-glob")
    r.add_argument("--map", action="append", help="T05=M03,M04 - this course's modules teaching a topic (repeatable)")

    w = sp.add_parser("withdraw", parents=[common])
    w.add_argument("what", choices=["picture", "document", "inbox"])
    w.add_argument("name", help="file name in contributions/ or documents/, or the inbox id (I001)")

    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.cmd in ("fact", "term", "regulation"):
        return inbox_add(a.cmd, a)
    return {"picture": picture, "document": document, "register-course": register_course, "withdraw": withdraw}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
