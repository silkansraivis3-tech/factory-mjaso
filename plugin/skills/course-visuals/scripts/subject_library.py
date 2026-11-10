#!/usr/bin/env python3
"""Find the shared course libraries, make a new one when a course needs it, and talk to them.

The course libraries live on the company's Drive, never in this repository, in ONE parent folder
`Course Libraries` (LIBRARIES.json = the registry): one library per subject (the Gas Library first,
which stays where it is and is listed by its absolute path) and `common` for what every course
shares. source/knowledge/subject-libraries.json says how to find them and where a finding goes;
source/library_template/ is what a new library starts with. A library that is not there is skipped
without a word - nothing in the factory depends on one.

  python subject_library.py ensure "<programme title, STCW ref, module titles>" [--json]
        [--subject-id <id> --name "<Name>" --subject-words w1,w2 [--stcw A-V/1-1-1]] [--course "<course>"]
      THE call at intake: the libraries this course uses, in reading order (its subject library, then
      common); makes common the first time, and the subject library when none matches and --subject-id
      is given. Exit 3 + a plain sentence when the model must choose an id, or no parent is reachable.
  python subject_library.py create --id <id> --name "<Name>" --subject-words w1,w2 [--stcw ...] [--parent <folder>]
      a new library from the template, registered in LIBRARIES.json
  python subject_library.py locate [--json]
      every library of the registry and of the config, each with whether it is there
  python subject_library.py covers "<programme title, STCW ref or module titles>"
      exit 0 + the subject library when a course on that text is on a library's subject, else exit 3
  python subject_library.py find "<subject>" [--json] [--only facts,glossary] [--course "<title>"] [--library <id>]
      the course's libraries together (subject first, then common), every result labelled with its library
  python subject_library.py route <kind> "<title or text>" [--source "<document>"] [--course "<title>"] [--general]
      which library a finding belongs in, and why, in one line
  python subject_library.py contribute [--library auto|<id>] [--course "<title>"] [--general]
        picture|document|fact|term|regulation|register-course|withdraw ...
      routes the finding (auto = the default), then runs that library's contribute.py
  python subject_library.py sync [--library <id>]
      rebuild a library (its build_library.py; the factory's kb_build.py makes its documents searchable)

Exit codes: 0 done / found, 3 no library here (or not on its subject, or a choice to make), 2 bad
usage or refused; any other code is the library tool's own.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
CONFIG = os.path.join(SKILL, "source", "knowledge", "subject-libraries.json")
TEMPLATE = os.path.join(SKILL, "source", "library_template")
KB_BUILDER = os.path.join(os.path.dirname(SKILL), "course-factory", "kb", "builder", "kb_build.py")
ENV_ALL = "NOVIKONTAS_SUBJECT_LIBRARIES"
ENV_PARENTS = "NOVIKONTAS_COURSE_LIBRARIES"
ID_RX = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
KINDS = ("picture", "document", "fact", "term", "regulation", "register-course", "withdraw")

PARENT_README = """# Course Libraries - read me first

The NOVIKONTAS course libraries: one shared knowledge base + asset library per subject, and `Common`
for what every course shares (STCW, SOLAS, MARPOL, ISM, COLREG, MLC, the general parts of the IMO
model courses, the pedagogy guideline, brand material).

- `LIBRARIES.json` - the registry: every library, its folder (relative to this one, or absolute when
  it lives elsewhere, like the Gas Library), its subject words, STCW references and courses.
- One folder per library; each has its own `00_READ_ME_FIRST.md`, `CLAUDE.md` and `tools/find.py`.

The Course Factory keeps this folder: `subject_library.py ensure` at a course's intake picks (or
makes) the course's libraries, `find` reads them, `contribute` puts each finding in the right one.
Do not rename a library folder without changing its `path` in `LIBRARIES.json`.
"""


class Refused(Exception):
    """A plain sentence for the person or the model; nothing was written."""


def config(path: str = CONFIG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _norm(p: str) -> str:
    return p.replace("\\", "/").rstrip("/")


def _key(p: str) -> str:
    return os.path.normcase(os.path.realpath(p))


def _off(v: str | None) -> bool:
    return (v or "").strip().lower() in ("off", "none", "0")


def _is_library(root: str, marker: list[str]) -> bool:
    return bool(root) and os.path.isdir(root) and all(os.path.exists(os.path.join(root, m)) for m in marker)


# ------------------------------------------------------------------ the parent folder and its registry

def parents(cfg: dict, env: dict) -> list[str]:
    """The Course Libraries folders to read, in order: the env var's, else the config's default places."""
    raw = (env.get(ENV_PARENTS) or "").strip()
    if raw:
        return [] if _off(raw) else [os.path.expanduser(p.strip()) for p in raw.split(os.pathsep) if p.strip()]
    return [os.path.expanduser(p) for p in cfg.get("course_libraries", {}).get("default_parents", [])]


def _registry_name(cfg: dict) -> str:
    return cfg.get("course_libraries", {}).get("registry", "LIBRARIES.json")


def read_registry(parent: str, cfg: dict) -> dict | None:
    try:
        with open(os.path.join(parent, _registry_name(cfg)), encoding="utf-8") as fh:
            reg = json.load(fh)
        return reg if isinstance(reg.get("libraries"), list) else None
    except (OSError, ValueError, AttributeError):
        return None


def write_registry(parent: str, reg: dict, cfg: dict) -> None:
    path = os.path.join(parent, _registry_name(cfg))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def home_parent(cfg: dict, env: dict) -> str | None:
    """Where libraries are made: the first parent that has a registry, else the first that can be made
    (its own folder or the folder above it exists - Drive is mounted). None = not reachable here."""
    ps = parents(cfg, env)
    for p in ps:
        if read_registry(p, cfg) is not None:
            return p
    for p in ps:
        if os.path.isdir(p) or os.path.isdir(os.path.dirname(os.path.normpath(p))):
            return p
    return None


def _root_of(parent: str, path: str) -> str:
    path = os.path.expanduser(path)
    return _norm(path if os.path.isabs(path) else os.path.join(parent, path))


def _entry(spec: dict, root: str, origin: str, marker: list[str] | None = None) -> dict:
    root = _norm(root)
    return {
        "id": spec["id"], "name": spec.get("name", spec["id"]), "root": root,
        "find": root + "/tools/find.py", "contribute": root + "/tools/contribute.py",
        "use_asset": root + "/tools/use_asset.py", "build": root + "/tools/build_library.py",
        "subject_words": spec.get("subject_words", []), "stcw": spec.get("stcw", []),
        "courses": spec.get("courses", []), "common": bool(spec.get("common")), "origin": origin,
        "present": _is_library(root, marker or ["tools/find.py"]),
    }


def catalogue(cfg: dict | None = None, env: dict | None = None) -> list[dict]:
    """Every library this computer knows of - registry, env folders, config - each with 'present'. Never raises."""
    env = os.environ if env is None else env
    try:
        cfg = cfg or config()
    except (OSError, ValueError):
        return []
    extra = (env.get(ENV_ALL) or "").strip()
    if _off(extra):
        return []
    out: list[dict] = []
    seen: set[str] = set()

    def add(e: dict) -> None:
        k = _key(e["root"])
        if k in seen:
            return
        if not e["present"] and any(x["id"] == e["id"] and x["present"] for x in out):
            return
        seen.add(k)
        out.append(e)

    for parent in parents(cfg, env):
        reg = read_registry(parent, cfg)
        for spec in (reg or {}).get("libraries", []):
            if spec.get("id") and spec.get("path"):
                add(_entry(spec, _root_of(parent, spec["path"]), "registry " + _norm(parent)))
    specs = cfg.get("libraries", [])
    for root in [os.path.expanduser(p.strip()) for p in extra.split(os.pathsep) if p.strip()]:
        if not _is_library(root, ["tools/find.py"]):
            continue
        folder = os.path.basename(os.path.normpath(root))
        # a known library by its folder name ("Gas Library") keeps its id and subject words
        spec = next((s for s in specs if any(os.path.basename(d) == folder for d in s.get("default_locations", []))),
                    {"id": re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-"), "name": folder})
        add(_entry(spec, root, "env " + ENV_ALL))
    explicit = bool((env.get(ENV_PARENTS) or "").strip())
    for spec in specs:
        marker = spec.get("marker", ["tools/find.py"])
        places = ([env[spec["env"]]] if spec.get("env") and env.get(spec["env"]) else []) + \
                 ([] if explicit else spec.get("default_locations", []))
        hit = next((os.path.expanduser(p) for p in places if _is_library(os.path.expanduser(p), marker)), None)
        if hit:
            add(_entry(spec, hit, "config", marker))
        elif places:
            add(_entry(spec, os.path.expanduser(places[0]), "config", marker))
    return out


def locate(cfg: dict | None = None, env: dict | None = None) -> list[dict]:
    """Every library present on this computer. Never raises; [] when there is none."""
    return [x for x in catalogue(cfg, env) if x["present"]]


def _low(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9\-/]+", " ", (text or "").lower()) + " "


def _hits(words: list[str], text: str) -> list[str]:
    low = _low(text)
    return [w for w in words if f" {w} " in low or (" " in w and w in low)]


def _stcw_hits(refs: list[str], text: str) -> list[str]:
    flat = re.sub(r"\s+", "", (text or "").upper())
    return [r for r in refs if re.search(re.escape(r.upper().replace(" ", "")) + r"(?![0-9])", flat)]


def covers(text: str, libs: list[dict]) -> list[dict]:
    """The subject libraries a course with this title / reference / module titles is on, best first."""
    scored = []
    for lib in libs:
        if lib.get("common"):
            continue
        n = len(_hits(lib.get("subject_words", []), text)) + 2 * len(_stcw_hits(lib.get("stcw", []), text))
        if n:
            scored.append((n, lib))
    scored.sort(key=lambda x: -x[0])
    return [lib for _, lib in scored]


# ------------------------------------------------------------------ making a library

def _repo_root() -> str | None:
    d = HERE
    while True:
        if os.path.isdir(os.path.join(d, ".git")) or os.path.isfile(os.path.join(d, ".git")):
            return d
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def _inside(child: str, parent: str) -> bool:
    try:
        return os.path.commonpath([_key(child), _key(parent)]) == _key(parent)
    except ValueError:
        return False


def _guard_place(folder: str) -> None:
    """Never into the factory repository, never into a course folder."""
    repo = _repo_root()
    if repo and _inside(folder, repo):
        raise Refused(f"{_norm(folder)} is inside the factory repository - a library lives on the Drive, never here")
    d = os.path.abspath(folder)
    while True:
        if os.path.isdir(os.path.join(d, "working_claude")) or os.path.isdir(os.path.join(d, "course", "modules")) \
                or os.path.isfile(os.path.join(d, "COURSE_LANGUAGE")):
            raise Refused(f"{_norm(folder)} is inside a course folder ({_norm(d)}) - a library never goes into a course")
        up = os.path.dirname(d)
        if up == d:
            return
        d = up


def open_registry(parent: str, cfg: dict, env: dict) -> dict:
    """The parent's registry; the parent, LIBRARIES.json and the README are made when missing, and every
    present library of the config (the Gas Library) is listed by its absolute path."""
    _guard_place(parent)
    os.makedirs(parent, exist_ok=True)
    reg = read_registry(parent, cfg)
    changed = reg is None
    if reg is None:
        reg = {"_about": "The NOVIKONTAS course libraries. path: relative to this folder, or absolute for a library "
                         "that lives elsewhere. Kept by the Course Factory (subject_library.py ensure / create).",
               "libraries": []}
    readme = os.path.join(parent, "00_READ_ME_FIRST.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(PARENT_README)
    ids = {x.get("id") for x in reg["libraries"]}
    for spec in cfg.get("libraries", []):
        if spec["id"] in ids:
            continue
        marker = spec.get("marker", ["tools/find.py"])
        places = ([env[spec["env"]]] if spec.get("env") and env.get(spec["env"]) else []) + \
                 ([] if (env.get(ENV_PARENTS) or "").strip() else spec.get("default_locations", []))
        hit = next((os.path.expanduser(p) for p in places if _is_library(os.path.expanduser(p), marker)), None)
        if hit:
            reg["libraries"].append({"id": spec["id"], "name": spec.get("name", spec["id"]),
                                     "path": _norm(os.path.abspath(hit)),
                                     "subject_words": spec.get("subject_words", []), "stcw": spec.get("stcw", []),
                                     "courses": spec.get("courses", []),
                                     "created": spec.get("created") or date.today().isoformat()})
            changed = True
    if changed:
        write_registry(parent, reg, cfg)
    return reg


def _words(v) -> list[str]:
    if isinstance(v, str):
        v = v.split(",")
    return [w.strip().lower() for w in (v or []) if w and w.strip()]


def create(lib_id: str, name: str, subject_words, stcw=None, parent: str | None = None, common: bool = False,
           folder: str | None = None, cfg: dict | None = None, env: dict | None = None) -> dict:
    """Make a library from the template under the parent and register it. Returns its entry; raises Refused."""
    env = os.environ if env is None else env
    cfg = cfg or config()
    if not ID_RX.match(lib_id or ""):
        raise Refused(f"id '{lib_id}' - use lower-case letters, digits and '-', e.g. 'fire-fighting'")
    if not (name or "").strip():
        raise Refused("give the library a name: --name \"NOVIKONTAS <Subject> Library\"")
    words = _words(subject_words)
    if not words:
        raise Refused("give the subject words a course title holds when it is on this subject: --subject-words w1,w2")
    parent = parent or home_parent(cfg, env)
    if not parent:
        raise Refused("no Course Libraries folder can be reached on this computer (Google Drive not mounted?)")
    _guard_place(parent)
    known = {x["id"] for x in catalogue(cfg, env)}
    reg = open_registry(parent, cfg, env)
    if lib_id in known or lib_id in {x.get("id") for x in reg["libraries"]}:
        raise Refused(f"a library with id '{lib_id}' exists already - use it, or choose another id")
    folder = folder or " ".join(p.capitalize() for p in lib_id.split("-"))
    dest = os.path.join(parent, folder)
    if os.path.exists(dest):
        raise Refused(f"{_norm(dest)} exists already - choose another id")
    refs = [r.strip() for r in (stcw.split(",") if isinstance(stcw, str) else (stcw or [])) if r and r.strip()]
    today = date.today().isoformat()
    shutil.copytree(TEMPLATE, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    subject = ", ".join(words)
    for base, _, files in os.walk(dest):
        for f in files:
            if f.endswith(".md"):
                p = os.path.join(base, f)
                with open(p, encoding="utf-8") as fh:
                    text = fh.read()
                text = (text.replace("{{LIBRARY_NAME}}", name.strip()).replace("{{SUBJECT}}", subject)
                        .replace("{{STCW}}", f" (STCW {', '.join(refs)})" if refs else "").replace("{{CREATED}}", today))
                with open(p, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
    cp = os.path.join(dest, "library_config.json")
    with open(cp, encoding="utf-8") as fh:
        lc = json.load(fh)
    lc.update({"library_id": lib_id, "library_name": name.strip(), "subject_words": words, "stcw": refs, "created": today})
    with open(cp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(lc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for sub in ("contributions", "retrieval", "courses"):
        os.makedirs(os.path.join(dest, sub), exist_ok=True)
    entry = {"id": lib_id, "name": name.strip(), "path": folder, "subject_words": words, "stcw": refs,
             "courses": [], "created": today}
    if common:
        entry["common"] = True
    reg["libraries"].append(entry)
    write_registry(parent, reg, cfg)
    return _entry(entry, dest, "registry " + _norm(parent))


def _common_spec(cfg: dict) -> dict:
    c = cfg.get("course_libraries", {}).get("common", {})
    return {"id": c.get("id", "common"), "name": c.get("name", "NOVIKONTAS Common Library"),
            "folder": c.get("folder", "Common"),
            "words": cfg.get("routing", {}).get("common_words", ["stcw", "solas", "marpol"])}


def _register_course(parent: str, ids: list[str], course: str, cfg: dict) -> None:
    reg = read_registry(parent, cfg)
    if not reg or not course:
        return
    changed = False
    for x in reg["libraries"]:
        if x.get("id") in ids and course not in x.setdefault("courses", []):
            x["courses"].append(course)
            changed = True
    if changed:
        write_registry(parent, reg, cfg)


def _brief(lib: dict, role: str, why: str) -> dict:
    return {"id": lib["id"], "name": lib["name"], "root": lib["root"], "role": role, "why": why,
            "find": lib["find"], "contribute": lib["contribute"], "use_asset": lib["use_asset"]}


def ensure(text: str, subject_id: str | None = None, name: str | None = None, subject_words=None, stcw=None,
           course: str | None = None, cfg: dict | None = None, env: dict | None = None) -> tuple[int, dict]:
    """The libraries a course uses, in reading order; makes what is missing. (exit code, result)."""
    env = os.environ if env is None else env
    cfg = cfg or config()
    parent = home_parent(cfg, env)
    if not parent:
        return 3, {"ok": False, "parent": None, "libraries": [], "created": [],
                   "say": "No Course Libraries folder can be reached on this computer (Google Drive is not mounted, "
                          f"or {ENV_PARENTS} points nowhere). The course goes on without a library: its own knowledge "
                          "base first, then the internet."}
    created: list[str] = []
    try:
        open_registry(parent, cfg, env)
        cs = _common_spec(cfg)
        libs = catalogue(cfg, env)
        if not any(x["common"] and x["present"] for x in libs):
            if any(x["id"] == cs["id"] for x in libs):
                return 3, {"ok": False, "parent": _norm(parent), "libraries": [], "created": [],
                           "say": f"The registry lists '{cs['id']}' but its folder is missing - restore it on the Drive "
                                  "or take its entry out of LIBRARIES.json."}
            create(cs["id"], cs["name"], cs["words"], parent=parent, common=True, folder=cs["folder"], cfg=cfg, env=env)
            created.append(cs["id"])
            libs = catalogue(cfg, env)
        present = [x for x in libs if x["present"]]
        common = [x for x in present if x["common"]]
        subj = covers(text, present)
        why = {x["id"]: "its subject words or STCW reference are in the programme" for x in subj}
        if subject_id and not subj:
            named = next((x for x in libs if x["id"] == subject_id), None)
            if named and named["present"] and not named["common"]:
                subj, why[subject_id] = [named], "named by --subject-id"
            elif named:
                return 3, {"ok": False, "parent": _norm(parent), "libraries": [], "created": created,
                           "say": f"'{subject_id}' is {'the common library' if named['common'] else 'registered but its folder is missing'}"
                                  " - choose another --subject-id."}
            else:
                if not (name and _words(subject_words)):
                    return 2, {"ok": False, "parent": _norm(parent), "libraries": [], "created": created,
                               "say": "--subject-id needs --name \"<Name>\" and --subject-words w1,w2 to make the library."}
                subj = [create(subject_id, name, subject_words, stcw, parent=parent, cfg=cfg, env=env)]
                created.append(subject_id)
                why[subject_id] = "none matched - made now from the template"
    except Refused as e:
        return 2, {"ok": False, "parent": _norm(parent), "libraries": [], "created": created, "say": str(e)}
    order = [_brief(x, "subject", why.get(x["id"], "")) for x in subj] + \
            [_brief(x, "common", "what every course shares") for x in common]
    if course:
        _register_course(parent, [x["id"] for x in order], course, cfg)
    res = {"ok": bool(subj), "parent": _norm(parent), "libraries": order, "created": created}
    if not subj:
        res["say"] = ("No subject library covers this course. Choose an id, a name and subject words from the "
                      "programme and call again: subject_library.py ensure \"<programme title, STCW ref>\" "
                      "--subject-id <id> --name \"NOVIKONTAS <Subject> Library\" --subject-words w1,w2 [--stcw <ref>]")
        return 3, res
    res["say"] = ("Read them in this order (subject_library.py find \"<subject>\" --course \"<title>\"), then the "
                  "course's knowledge base, then the internet; save each finding back with subject_library.py "
                  "contribute --course \"<title>\" ... (it picks the library).")
    return 0, res


# ------------------------------------------------------------------ where a finding goes

def _subject_for(course: str | None, text: str, present: list[dict]) -> list[dict]:
    if course:
        hit = covers(course, present)
        if hit:
            return hit
    hit = covers(text, present)
    if hit:
        return hit
    subj = [x for x in present if not x["common"]]
    return subj if len(subj) == 1 else []


def route(kind: str, text: str, source: str = "", course: str | None = None, library: str | None = None,
          general: bool = False, cfg: dict | None = None, env: dict | None = None) -> tuple[int, dict]:
    """Which library a finding goes into: (exit code, {library, name, root, contribute, why})."""
    env = os.environ if env is None else env
    cfg = cfg or config()
    R = cfg.get("routing", {})
    present = locate(cfg, env)
    out = lambda lib, why: (0, {"library": lib["id"], "name": lib["name"], "root": lib["root"],  # noqa: E731
                                "contribute": lib["contribute"], "why": why})
    if kind not in KINDS:
        return 2, {"library": None, "why": f"kind '{kind}' - one of {', '.join(KINDS)}"}
    if library and library != "auto":
        lib = next((x for x in present if x["id"] == library), None)
        if not lib:
            return 3, {"library": None, "why": f"no library '{library}' on this computer ({', '.join(x['id'] for x in present) or 'none'})"}
        return out(lib, f"--library {library} given")
    if kind == "withdraw":
        return 2, {"library": None, "why": "withdraw needs --library <id> - say which library it was added to"}
    common = next((x for x in present if x["common"]), None)
    subj = _subject_for(course, f"{text} {source}", present)
    target, why = None, ""
    if kind in R.get("source_kinds", ["document", "fact", "term", "regulation"]):
        hay = source if (source or "").strip() else text
        m = _hits(R.get("common_words", []), hay)
        # a fact or a term ABOUT the course's subject stays with the subject, whatever convention it is quoted from
        about = kind in ("fact", "term") and subj and _hits(subj[0]["subject_words"], text)
        if m and not about:
            target = common
            why = (f"its {'source' if (source or '').strip() else 'title'} names {m[0].upper()}, which applies to every "
                   f"ship type -> {common['name'] if common else 'common'}")
    elif kind == "picture":
        g = _hits(R.get("general_picture_words", []), text)
        s = _hits(subj[0]["subject_words"], text) if subj else []
        if general or (g and not s):
            target = common
            why = (f"a general picture ({'--general' if general else g[0]}) serves every course -> "
                   f"{common['name'] if common else 'common'}")
    if why:
        if not target:
            return 3, {"library": "common", "why": why + " - but common is not here: run subject_library.py ensure first"}
        return out(target, why)
    if not subj:
        return 3, {"library": None, "why": "no subject library for this course - run subject_library.py ensure "
                                           "\"<programme>\" first, give --course \"<title>\", or pass --library common"}
    what = {"picture": "a picture on", "register-course": "a course on"}.get(kind, f"a {kind} on")
    return out(subj[0], f"{what} the course's subject -> {subj[0]['name']}")


def _opt(rest: list[str], flag: str) -> str:
    for i, x in enumerate(rest):
        if x == flag and i + 1 < len(rest):
            return rest[i + 1]
        if x.startswith(flag + "="):
            return x.split("=", 1)[1]
    return ""


def _positionals(rest: list[str]) -> list[str]:
    out, skip = [], False
    for x in rest:
        if skip:
            skip = False
            continue
        if x.startswith("--"):
            skip = "=" not in x and x not in ("--no-rebuild",)
            continue
        out.append(x)
    return out


def finding_text(kind: str, rest: list[str]) -> tuple[str, str]:
    """(text, source) of a contribute call, for routing."""
    pos = _positionals(rest)
    if kind in ("fact", "term", "regulation"):
        return " ".join(pos[:2]), _opt(rest, "--source")
    if kind == "document":
        return " ".join([_opt(rest, "--title"), os.path.basename(pos[0]) if pos else "", _opt(rest, "--type")]), \
            _opt(rest, "--title")
    if kind == "picture":
        bits = [_opt(rest, "--description"), " ".join(_opt(rest, f) for f in ("--teaching-purpose", "--shows"))]
        if pos and os.path.isfile(pos[0]):
            for meta in ("_photo_meta.json", "_figure_meta.json", "_sim_meta.json"):
                p = os.path.join(os.path.dirname(pos[0]), meta)
                try:
                    with open(p, encoding="utf-8") as fh:
                        rec = json.load(fh).get(os.path.basename(pos[0]))
                except (OSError, ValueError):
                    continue
                if isinstance(rec, dict):
                    bits += [str(rec.get(k) or "") for k in ("description", "shows", "teaching_purpose")]
                    break
        return " ".join(b for b in bits if b), ""
    if kind == "register-course":
        return " ".join([_opt(rest, "--title")] + pos[:1]), ""
    return " ".join(pos), ""


def _supports(lib: dict, kind: str) -> bool:
    try:
        p = _run(lib["contribute"], ["--help"], timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    m = re.search(r"\{([a-z,\-]+)\}", p.stdout or "")
    return bool(m) and kind in m.group(1).split(",")


# ------------------------------------------------------------------ reading

def _run(script: str, args: list[str], timeout: int = 180, capture: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")  # no __pycache__ on the Drive
    if os.path.isfile(KB_BUILDER):
        env.setdefault("NOVIKONTAS_KB_BUILDER", KB_BUILDER)
    return subprocess.run([sys.executable, script] + args, capture_output=capture, text=capture,
                          encoding="utf-8" if capture else None, errors="replace" if capture else None,
                          env=env, timeout=timeout)


def find_json(lib: dict, query: str, only: str | None = None, pictures: int = 8, timeout: int = 90) -> dict | None:
    """The library's find.py --json; None when it cannot answer (never raises)."""
    args = [query, "--json", "--pictures", str(pictures)]
    try:
        p = _run(lib["find"], args + (["--only", only] if only else []), timeout)
        if p.returncode == 2 and "--only" in (p.stderr or ""):  # an older find.py: ask for everything
            p = _run(lib["find"], args, timeout)
        return json.loads(p.stdout) if p.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def reading_order(course: str | None, libs: list[dict]) -> list[dict]:
    """Subject libraries first (the course's, when a course is named), then common."""
    subj = covers(course, libs) if course else [x for x in libs if not x["common"]]
    return subj + [x for x in libs if x["common"]]


def find_all(query: str, libs: list[dict], only: str | None = None, timeout: int = 300) -> dict:
    """Every library's find.py --json merged, each result labelled with its library; each library's own
    flags kept (CONFLICT, rights state, distribution)."""
    sections = ("topics", "facts", "glossary", "regulations", "inbox_not_reviewed", "pictures", "documents", "passages")
    out: dict = {"query": query, "libraries": [], **{s: [] for s in sections}}
    for lib in libs:
        d = find_json(lib, query, only=only, timeout=timeout)
        role = "common" if lib["common"] else "subject"
        if d is None:
            out["libraries"].append({"id": lib["id"], "name": lib["name"], "role": role, "answered": False})
            continue
        out["libraries"].append({"id": lib["id"], "name": lib["name"], "role": role, "answered": True,
                                 "searchable": d.get("searchable", True), "not_searchable": d.get("not_searchable"),
                                 "also_searched_as": d.get("also_searched_as", [])})
        for s in sections:
            for item in d.get(s) or []:
                if isinstance(item, dict):
                    item = dict(item, library=lib["id"])
                    if s == "facts":
                        item["conflict"] = any("CONFLICT" in str(c) for c in item.get("row", []))
                    if s == "documents":
                        item["to_trainees"] = item.get("distribution") in ("SHARE", "FREE_DOWNLOAD")
                else:
                    item = {"library": lib["id"], "row": item}
                    if s == "inbox_not_reviewed":
                        item["status"] = item["row"][2] if len(item["row"]) > 2 else ""
                out[s].append(item)
    return out


def strong(match: dict | None) -> bool:
    """A description that says what was asked: the phrase (or a synonym of it), or most of its words.
    One shared word ('unit' in 'gas valve unit') is a coincidence, not a candidate - a one-word
    need is met by its phrase match."""
    if not match:  # an older find.py gives no match - keep what it ranked
        return True
    if match.get("phrase"):
        return True
    return match.get("words", 0) >= max(2, ((match.get("of") or 0) + 1) // 2)


def pictures(query: str, libs: list[dict], limit: int = 8, allow_ai: bool = False,
             ship_states: set[str] | None = None) -> dict:
    """Library pictures for a need, rights-gated: {usable, ai_held_back, blocked, searched}."""
    if ship_states is None:
        try:
            ship_states = set(config()["ship_states"])
        except (OSError, ValueError, KeyError):
            ship_states = {"PUBLIC_DOMAIN", "ATTRIBUTION_REQUIRED", "CLEARED", "OWNER_CLEARED", "PROJECT_OWNED", "GENERATED"}
    out: dict = {"usable": [], "ai_held_back": [], "blocked": [], "searched": []}
    for lib in libs:
        d = find_json(lib, query, only="pictures", pictures=limit)
        if d is None:
            out["searched"].append(f"{lib['name']}: did not answer - skipped")
            continue
        pics = d.get("pictures") or []
        out["searched"].append(f"{lib['name']}: {len(pics)} by description"
                               + (f" (also as: {', '.join(d.get('also_searched_as') or [])})" if d.get("also_searched_as") else ""))
        for rank, p in enumerate(pics):
            if not strong(p.get("match")):
                continue
            c = {
                "level": 2, "level_name": "LIBRARY", "library": lib["name"], "library_id": p.get("id"),
                "path": (p.get("path") or "").replace("\\", "/"), "score": 100 - rank,
                "kind": p.get("kind"), "rights_state": p.get("rights_state") or "UNKNOWN",
                "ai_generated": bool(p.get("ai_generated")), "credit": p.get("credit"), "licence": p.get("licence"),
                "page_url": p.get("page_url"), "visually_verified": p.get("visually_verified") or "",
                "caption_caveat": p.get("caption_caveat"), "courses": p.get("courses") or [],
                "note": p.get("description") or "",
                "use": f'python "{lib["use_asset"]}" {p.get("id")} "<module folder>"',
            }
            if c["rights_state"] not in ship_states:
                c["why"] = "classroom reference only until cleared - not for the tablets"
                out["blocked"].append(c)
            elif c["ai_generated"] and not allow_ai:
                c["why"] = "AI picture - never the picture of equipment a trainee must recognise (--allow-ai for a scene or cutaway)"
                out["ai_held_back"].append(c)
            else:
                if c["ai_generated"]:
                    c["why"] = "AI picture - a scene or cutaway only, never equipment a trainee must recognise"
                out["usable"].append(c)
    return out


# ------------------------------------------------------------------ the command line

def _print(res: dict, as_json: bool, lines) -> None:
    if as_json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        for line in lines(res):
            print(line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    lo = sp.add_parser("locate")
    lo.add_argument("--json", action="store_true")
    cv = sp.add_parser("covers")
    cv.add_argument("text")
    en = sp.add_parser("ensure")
    en.add_argument("text")
    en.add_argument("--subject-id")
    en.add_argument("--name")
    en.add_argument("--subject-words")
    en.add_argument("--stcw")
    en.add_argument("--course", help="the course's name, recorded with each library it uses")
    en.add_argument("--json", action="store_true")
    cr = sp.add_parser("create")
    cr.add_argument("--id", required=True)
    cr.add_argument("--name", required=True)
    cr.add_argument("--subject-words", required=True)
    cr.add_argument("--stcw")
    cr.add_argument("--parent")
    cr.add_argument("--json", action="store_true")
    ro = sp.add_parser("route")
    ro.add_argument("kind", choices=KINDS)
    ro.add_argument("text")
    ro.add_argument("--source", default="")
    ro.add_argument("--course")
    ro.add_argument("--library")
    ro.add_argument("--general", action="store_true")
    ro.add_argument("--json", action="store_true")
    fi = sp.add_parser("find")
    fi.add_argument("query")
    fi.add_argument("--json", action="store_true")
    fi.add_argument("--only")
    fi.add_argument("--library")
    fi.add_argument("--course")
    co = sp.add_parser("contribute")
    co.add_argument("--library", default="auto")
    co.add_argument("--course")
    co.add_argument("--general", action="store_true")
    co.add_argument("rest", nargs=argparse.REMAINDER)
    sy = sp.add_parser("sync")
    sy.add_argument("--library")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.cmd == "ensure":
        code, res = ensure(a.text, a.subject_id, a.name, a.subject_words, a.stcw, a.course)
        _print(res, a.json, lambda r: [f"{i}. {x['id']:10} {x['name']}  {x['root']}  ({x['role']}: {x['why']})"
                                       for i, x in enumerate(r["libraries"], 1)]
               + ([f"made now: {', '.join(r['created'])}"] if r.get("created") else []) + [r.get("say", "")])
        return code
    if a.cmd == "create":
        try:
            e = create(a.id, a.name, a.subject_words, a.stcw, parent=a.parent)
        except Refused as ex:
            print(f"REFUSED - {ex}")
            return 2
        _print(e, a.json, lambda r: [f"made {r['id']} ({r['name']}) at {r['root']} - registered in LIBRARIES.json"])
        return 0
    if a.cmd == "route":
        code, res = route(a.kind, a.text, a.source, a.course, a.library, a.general)
        _print(res, a.json, lambda r: [f"{r.get('library') or '-'}: {r['why']}"])
        return code
    if a.cmd == "locate":
        cat = catalogue()
        if a.json:
            print(json.dumps(cat, indent=2, ensure_ascii=False))
        elif not cat:
            print("no course library known on this computer - the factory works without one")
        for lib in ([] if a.json else cat):
            print(f"{lib['id']:10} {'here   ' if lib['present'] else 'MISSING'} {lib['name']}  {lib['root']}"
                  f"  [{'common' if lib['common'] else 'subject'}; {lib['origin']}]")
            if lib["present"]:
                print(f"           find:       python \"{lib['find']}\" \"<subject>\"")
        return 0 if any(x["present"] for x in cat) else 3

    libs = locate()
    if a.cmd == "covers":
        hit = covers(a.text, libs)
        for lib in hit:
            print(f"{lib['id']}  {lib['name']}  {lib['root']}")
        if not hit:
            print("no library here covers this subject" if libs else "no subject library on this computer")
        return 0 if hit else 3
    if a.cmd == "contribute":
        rest = a.rest[1:] if a.rest[:1] == ["--"] else list(a.rest)
        for flag in ("--library", "--course"):  # client options given after the kind
            v = _opt(rest, flag)
            if v:
                setattr(a, flag[2:], v)
                i = rest.index(flag) if flag in rest else next(i for i, x in enumerate(rest) if x.startswith(flag + "="))
                del rest[i:i + (2 if rest[i] == flag else 1)]
        if "--general" in rest:
            a.general = True
            rest.remove("--general")
        if not rest or rest[0] not in KINDS:
            print("say what: picture | document | fact | term | regulation | register-course | withdraw "
                  "(see --help of the library's contribute.py)")
            return 2
        text, source = finding_text(rest[0], rest[1:])
        code, res = route(rest[0], text, source, a.course, a.library, a.general)
        print(f"-> {res.get('library') or '-'}: {res['why']}")
        if code:
            return code
        lib = next(x for x in libs if x["id"] == res["library"])
        if rest[0] == "regulation" and not _supports(lib, "regulation"):
            rest = ["fact"] + rest[1:] + ["--note", "regulation"]
        return _run(lib["contribute"], rest, timeout=900, capture=False).returncode

    if a.cmd == "find":
        chosen = [x for x in libs if x["id"] == a.library] if a.library else reading_order(a.course, libs)
        if not chosen:
            print("no course library on this computer" + (f" with id '{a.library}'" if a.library else "") +
                  " - skipped (search the knowledge base, then level 3)")
            return 3
        if a.json:
            print(json.dumps(find_all(a.query, chosen, a.only), ensure_ascii=False, indent=1))
            return 0
        rc = 0
        for lib in chosen:
            print(f"\n=== {lib['name']} [{lib['id']}, {'common' if lib['common'] else 'subject'}] ===")
            sys.stdout.flush()
            p = _run(lib["find"], [a.query] + (["--only", a.only] if a.only else []), timeout=600, capture=False)
            rc = rc or p.returncode
        return rc

    chosen = [x for x in libs if x["id"] == a.library] if a.library else libs
    if not chosen:
        print("no course library on this computer" + (f" with id '{a.library}'" if a.library else "") + " - skipped")
        return 3
    if len(chosen) > 1:
        print("several libraries here - say which: --library " + " | ".join(lib["id"] for lib in chosen))
        return 2
    return _run(chosen[0]["build"], [], timeout=3600, capture=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
