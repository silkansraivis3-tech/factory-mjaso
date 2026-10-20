#!/usr/bin/env python3
"""Find the shared subject libraries and talk to them - read, and save back.

A subject library (the NOVIKONTAS Gas Library is the first) is one knowledge base + asset library
shared by every course on its subject. It lives on the company's Drive, never in this repository;
source/knowledge/subject-libraries.json says how to find it. A library that is not there is skipped
without a word - nothing in the factory depends on one.

  python subject_library.py locate [--json]
      which libraries this computer has, and the commands for each
  python subject_library.py covers "<programme title, STCW ref or module titles>"
      exit 0 + the library when a course on that text is on a library's subject, else exit 3
  python subject_library.py find "<subject>" [--json] [--only facts,glossary] [--library gas]
      the library's find.py: topics and modules, cited facts (CONFLICT rows flagged - not settled),
      glossary, regulations, the unreviewed inbox, pictures with rights, reference PDFs with
      distribution, source passages with file + page
  python subject_library.py contribute [--library gas] picture|document|fact|term|register-course ...
      the library's contribute.py - saves back what a course session found (see its --help)
  python subject_library.py sync [--library gas]
      rebuild the library (its build_library.py harvests every registered course's pictures)

Exit codes: 0 done / found, 3 no library here (or not on its subject), 2 bad usage; any other code
is the library tool's own.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(os.path.dirname(HERE), "source", "knowledge", "subject-libraries.json")
ENV_ALL = "NOVIKONTAS_SUBJECT_LIBRARIES"


def config(path: str = CONFIG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _is_library(root: str, marker: list[str]) -> bool:
    return bool(root) and os.path.isdir(root) and all(os.path.exists(os.path.join(root, m)) for m in marker)


def locate(cfg: dict | None = None, env: dict | None = None) -> list[dict]:
    """Every library present on this computer. Never raises; [] when there is none."""
    env = os.environ if env is None else env
    try:
        cfg = cfg or config()
    except (OSError, ValueError):
        return []
    extra = (env.get(ENV_ALL) or "").strip()
    if extra.lower() in ("off", "none", "0"):
        return []
    found: list[dict] = []
    seen: set[str] = set()

    def add(spec: dict, root: str) -> None:
        real = os.path.normcase(os.path.realpath(root))
        if real in seen:
            return
        seen.add(real)
        root = root.replace("\\", "/").rstrip("/")
        found.append({
            "id": spec["id"], "name": spec.get("name", spec["id"]), "root": root,
            "find": root + "/tools/find.py",
            "contribute": root + "/tools/contribute.py",
            "use_asset": root + "/tools/use_asset.py",
            "build": root + "/tools/build_library.py",
            "subject_words": spec.get("subject_words", []),
        })

    specs = cfg.get("libraries", [])
    for root in [os.path.expanduser(p.strip()) for p in extra.split(os.pathsep) if p.strip()]:
        if not _is_library(root, ["tools/find.py"]):
            continue
        folder = os.path.basename(os.path.normpath(root))
        # a known library by its folder name ("Gas Library") keeps its id and subject words
        spec = next((s for s in specs if any(os.path.basename(d) == folder for d in s.get("default_locations", []))),
                    {"id": re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-"), "name": folder})
        add(spec, root)
    for spec in specs:
        marker = spec.get("marker", ["tools/find.py"])
        places = ([env[spec["env"]]] if spec.get("env") and env.get(spec["env"]) else []) + spec.get("default_locations", [])
        for p in places:
            p = os.path.expanduser(p)
            if _is_library(p, marker):
                add(spec, p)
                break
    return found


def covers(text: str, libs: list[dict]) -> list[dict]:
    """The libraries whose subject a course with this title / reference / module titles is on."""
    low = " " + re.sub(r"[^a-z0-9\-]+", " ", (text or "").lower()) + " "
    return [lib for lib in libs if any(f" {w} " in low or (" " in w and w in low) for w in lib["subject_words"])]


def _run(script: str, args: list[str], timeout: int = 180, capture: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
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


def _pick(libs: list[dict], want: str | None) -> list[dict]:
    if want:
        return [lib for lib in libs if lib["id"] == want]
    return libs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    lo = sp.add_parser("locate")
    lo.add_argument("--json", action="store_true")
    cv = sp.add_parser("covers")
    cv.add_argument("text")
    fi = sp.add_parser("find")
    fi.add_argument("query")
    fi.add_argument("--json", action="store_true")
    fi.add_argument("--only")
    fi.add_argument("--library")
    co = sp.add_parser("contribute")
    co.add_argument("--library")
    co.add_argument("rest", nargs=argparse.REMAINDER)
    sy = sp.add_parser("sync")
    sy.add_argument("--library")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    libs = _pick(locate(), getattr(a, "library", None))
    if a.cmd == "locate":
        if a.json:
            print(json.dumps(libs, indent=2, ensure_ascii=False))
        elif not libs:
            print("no subject library on this computer - the factory works without one")
        for lib in ([] if a.json else libs):
            print(f"{lib['id']:8} {lib['name']}  {lib['root']}")
            print(f"         find:       python \"{lib['find']}\" \"<subject>\"")
            print(f"         contribute: python \"{lib['contribute']}\" picture|document|fact|term|register-course ...")
        return 0 if libs else 3
    if a.cmd == "covers":
        hit = covers(a.text, libs)
        for lib in hit:
            print(f"{lib['id']}  {lib['name']}  {lib['root']}")
        if not hit:
            print("no library here covers this subject" if libs else "no subject library on this computer")
        return 0 if hit else 3
    if not libs:
        print("no subject library on this computer" + (f" with id '{a.library}'" if a.library else "") +
              " - skipped (search the knowledge base, then level 3)")
        return 3
    if a.cmd == "find":
        rc = 0
        for lib in libs:
            args = [a.query] + (["--json"] if a.json else []) + (["--only", a.only] if a.only else [])
            p = _run(lib["find"], args, capture=False)
            rc = rc or p.returncode
        return rc
    if len(libs) > 1:
        print("several libraries here - say which: --library " + " | ".join(lib["id"] for lib in libs))
        return 2
    if a.cmd == "contribute":
        rest = a.rest[1:] if a.rest[:1] == ["--"] else a.rest
        if not rest:
            print("say what: picture | document | fact | term | register-course | withdraw (see --help of contribute.py)")
            return 2
        return _run(libs[0]["contribute"], rest, timeout=900, capture=False).returncode
    return _run(libs[0]["build"], [], timeout=900, capture=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(2)
