#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The publication gate: may this course reach the shared platform repository?

Eight checks, run in one pass over the files the course actually publishes.
Every one of them exists because its failure is invisible until it is
expensive: a leaked answer key is only discovered by a trainee, a remote
font by a classroom with no Wi-Fi, a hardcoded laptop IP by a class in a
different building, a `.bak` file by nobody at all - it just ships.

    identity     the course knows what it is: id, title, version, modules
    roles        every published file is TRAINEE / INSTRUCTOR / SHARED /
                 INTERNAL, and no instructor-only material sits in the
                 trainee tree
    secrets      no credential of any kind, with one documented exception
    offline      nothing the page needs to be readable comes off a network
    addresses    no developer machine, localhost or LAN address in content
                 that ships
    junk         no .bak / .orig / editor state inside an asset tree
    assets       every local file a published page points at exists
    rights       figures whose own metadata says "not cleared for
                 publication" are named, so a human decides

Verdict: PASS, WARN (publishable, with things a human should read) or FAIL
(publication stops). Writes a JSON report that gitpub.py refuses to commit
without.

Usage
-----
    gates.py --repo <android project> --course-id gas-basic \\
             [--report out.json] [--strict] [--simulate-leak] [--quiet]

`--strict` promotes every WARN to a FAIL. Use it for a released course.
`--simulate-leak` and `--simulate-missing-asset` inject a fake finding so the
gate itself can be tested without breaking a real course.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLATFORM = os.path.join(os.path.dirname(HERE), "knowledge", "platform.json")
BASELINE = os.path.join(os.path.dirname(HERE), "knowledge", "known-findings.json")

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
TEXT_EXT = {".html", ".htm", ".js", ".css", ".json", ".svg", ".txt", ".md", ".csv"}


# ----------------------------------------------------------------- small utils
def load_platform(path: str = PLATFORM) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
JS_BLOCK = re.compile(r"/\*.*?\*/", re.S)
JS_LINE = re.compile(r"(?m)(?<![:\w])//[^\n]*$")


def strip_comments(txt, ext):
    """Comments are not shipped content, and matching them produced three of
    the first five role findings on this platform: a comment citing the answer
    key as a source is the opposite of a leak."""
    txt = HTML_COMMENT.sub(" ", txt)
    if ext in (".js", ".css", ".html", ".htm"):
        txt = JS_BLOCK.sub(" ", txt)
    if ext == ".js":
        txt = JS_LINE.sub(" ", txt)
    return txt


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def rel(repo: str, path: str) -> str:
    return os.path.relpath(path, repo).replace("\\", "/")


class Finding:
    __slots__ = ("check", "level", "path", "line", "detail")

    def __init__(self, check, level, path, line, detail):
        self.check, self.level, self.path, self.line, self.detail = check, level, path, line, detail

    def as_dict(self):
        return {"check": self.check, "level": self.level, "path": self.path,
                "line": self.line, "detail": self.detail}

    def __str__(self):
        where = self.path + (":" + str(self.line) if self.line else "")
        return f"[{self.level}] {self.check}: {where} - {self.detail}"


# -------------------------------------------------------------- the file sets
def course_file_sets(repo: str, plat: dict, course_id: str) -> dict:
    """Which real directories does this course publish, and in which role?

    Returns {"trainee": [dirs], "instructor": [dirs], "layout": "pack"|"legacy"}.
    Both layouts are supported deliberately: the platform's own contract
    specifies a nested course pack, and the course that exists today predates
    it. Converting a working course is a separate, human-authorised job.
    """
    roots = plat["asset_roots"]
    tr_root = os.path.join(repo, roots["trainee"].replace("/", os.sep))
    in_root = os.path.join(repo, roots["instructor"].replace("/", os.sep))

    pack_tr = os.path.join(tr_root, "courses", course_id)
    if os.path.isdir(pack_tr):
        pack_in = os.path.join(in_root, "courses", course_id)
        return {"layout": "pack",
                "trainee": [pack_tr],
                "instructor": [pack_in] if os.path.isdir(pack_in) else []}

    legacy = plat.get("legacy_courses", {}).get(course_id)
    if legacy:
        return {"layout": "legacy",
                "trainee": [os.path.join(repo, p.replace("/", os.sep))
                            for p in legacy.get("trainee_paths", [])
                            if os.path.exists(os.path.join(repo, p.replace("/", os.sep)))],
                "instructor": [os.path.join(repo, p.replace("/", os.sep))
                               for p in legacy.get("instructor_paths", [])
                               if os.path.exists(os.path.join(repo, p.replace("/", os.sep)))]}
    return {"layout": "unknown", "trainee": [], "instructor": []}


# -------------------------------------------------------------------- 1 identity
def check_identity(repo: str, plat: dict, course_id: str, sets: dict, out: list) -> dict:
    """A course must be able to say what it is. In the pack layout that is
    course.json; a legacy course is described by the platform file instead,
    and says so."""
    meta = {}
    if sets["layout"] == "pack":
        cj = os.path.join(sets["trainee"][0], "course.json")
        if not os.path.isfile(cj):
            out.append(Finding("identity", FAIL, rel(repo, cj), 0,
                               "a course pack must carry course.json (id, title, version, modules)"))
            return meta
        try:
            meta = json.loads(read_text(cj))
        except ValueError as e:
            out.append(Finding("identity", FAIL, rel(repo, cj), 0, "course.json is not valid JSON: " + str(e)))
            return meta
        for field in ("id", "title", "version", "modules"):
            if not meta.get(field):
                out.append(Finding("identity", FAIL, rel(repo, cj), 0, "course.json is missing '" + field + "'"))
        if meta.get("id") and meta["id"] != course_id:
            out.append(Finding("identity", FAIL, rel(repo, cj), 0,
                               f"course.json id '{meta['id']}' does not match the folder '{course_id}'"))
        v = str(meta.get("version", ""))
        if v and not re.match(r"^\d+\.\d+(\.\d+)?$", v):
            out.append(Finding("identity", WARN, rel(repo, cj), 0,
                               f"version '{v}' is not MAJOR.MINOR[.PATCH]; ordering releases will be guesswork"))
        if meta.get("status") == "released" and meta.get("allow_overwrite") is not True:
            meta["_released"] = True
    elif sets["layout"] == "legacy":
        leg = plat["legacy_courses"][course_id]
        meta = {"id": course_id, "title": leg.get("title", course_id),
                "version": leg.get("version", "0.0.0"), "layout": "legacy",
                "modules": leg.get("modules"), "_legacy_note": leg.get("note", "")}
        out.append(Finding("identity", WARN, "-", 0,
                           "legacy layout: this course is not a nested course pack, so its files "
                           "sit at the terminal root. It is publishable, but a second course "
                           "cannot use the same paths. See references/course-package.md."))
    else:
        out.append(Finding("identity", FAIL, "-", 0,
                           f"cannot find course '{course_id}': no courses/{course_id}/ pack and no "
                           "legacy entry in knowledge/platform.json"))
    if not sets["trainee"]:
        out.append(Finding("identity", FAIL, "-", 0, "no trainee-facing content found for this course"))
    return meta


# ----------------------------------------------------------------------- 2 roles
def classify(repo: str, plat: dict, path: str) -> str:
    r = rel(repo, path)
    roots = plat["asset_roots"]
    shared = plat["role_rules"]["shared_engine_globs"]
    name = os.path.basename(r)
    for pat in plat["role_rules"]["internal_globs"]:
        if re.search(pat, r, re.I):
            return "INTERNAL"
    if r.startswith(roots["instructor"]):
        return "INSTRUCTOR"
    if r.startswith(roots["trainee"]):
        depth = r[len(roots["trainee"]):].strip("/").count("/")
        if depth == 0 and any(re.fullmatch(g.replace("*", ".*"), name) for g in shared):
            return "SHARED"
        return "TRAINEE"
    return "INTERNAL"


def check_roles(repo: str, plat: dict, sets: dict, out: list, simulate: bool) -> dict:
    """The hard requirement. The platform enforces it structurally - the
    trainee APK does not package src/instructor/assets at all - so this check
    exists to catch the one thing that defeats structure: an instructor-only
    FILE placed in the trainee tree by hand."""
    rules = plat["role_rules"]
    counts = {"TRAINEE": 0, "INSTRUCTOR": 0, "SHARED": 0, "INTERNAL": 0}
    allow = {a["path"]: a["reason"] for a in rules.get("trainee_allowlist", [])}

    name_sigs = [(re.compile(p, re.I), why) for p, why in rules["instructor_only_filename_patterns"]]
    text_sigs = [(re.compile(p), lvl, why)
                 for p, lvl, why in rules["instructor_only_content_patterns"]]

    for root in sets["trainee"]:
        for f in walk(root):
            r = rel(repo, f)
            counts[classify(repo, plat, f)] += 1
            if r in allow:
                out.append(Finding("roles", "NOTE", r, 0, "allowlisted: " + allow[r]))
                continue
            for rx, why in name_sigs:
                if rx.search(os.path.basename(r)):
                    out.append(Finding("roles", FAIL, r, 0,
                                       "instructor-only material in the TRAINEE tree - " + why))
                    break
            ext = os.path.splitext(r)[1].lower()
            if ext in TEXT_EXT:
                txt = strip_comments(read_text(f), ext)
                for rx, lvl, why in text_sigs:
                    m = rx.search(txt)
                    if m:
                        line = txt.count("\n", 0, m.start()) + 1
                        out.append(Finding("roles", lvl, r, line,
                                           "instructor-only content in the TRAINEE tree - " + why
                                           + " (matched: " + m.group(0)[:60].replace("\n", " ") + ")"))
                        break

    for root in sets["instructor"]:
        for f in walk(root):
            counts[classify(repo, plat, f)] += 1

    if simulate:
        out.append(Finding("roles", FAIL, "SIMULATED/answer_key.html", 0,
                           "SIMULATED leak (--simulate-leak): proves the gate refuses"))
    return counts


# --------------------------------------------------------------------- 3 secrets
def check_secrets(repo: str, plat: dict, sets: dict, out: list) -> None:
    rules = plat["safety_rules"]["secrets"]
    pats = [(re.compile(p, re.I), lvl, why) for p, lvl, why in rules["patterns"]]
    allow = [re.compile(p) for p in rules.get("allow_patterns", [])]

    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            if os.path.splitext(f)[1].lower() not in TEXT_EXT:
                continue
            txt = read_text(f)
            for rx, lvl, why in pats:
                for m in rx.finditer(txt):
                    hit = m.group(0)
                    if any(a.search(hit) for a in allow):
                        continue
                    seg = txt[max(0, m.start() - 200): m.end() + 200]
                    if any(a.search(seg) for a in allow):
                        continue
                    out.append(Finding("secrets", lvl, rel(repo, f),
                                       txt.count("\n", 0, m.start()) + 1,
                                       why + " (matched: " + hit[:40] + "...)"))
                    break


# --------------------------------------------------------------------- 4 offline
REMOTE_SCRIPT = re.compile(r"<script[^>]+src\s*=\s*[\"'](https?:)?//([^\"']+)", re.I)
REMOTE_STYLE = re.compile(r"<link[^>]+href\s*=\s*[\"'](https?:)?//([^\"']+)", re.I)
GENERIC_FAMILIES = ("sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy")


def check_offline(repo: str, plat: dict, sets: dict, out: list) -> None:
    """A classroom tablet may have no network. The distinction that matters:
    a remote SCRIPT or a remote STYLESHEET the page needs in order to be
    readable is a failure; a remote FONT whose stack ends in a generic family
    degrades to a chosen fallback and is a warning. GAS BASIC pulls Raleway
    on ~105 pages and every stack ends in a generic family - so this must
    report, not block, or nothing could ever be published."""
    font_hosts = tuple(plat["safety_rules"]["offline"]["font_hosts"])

    # Font STACKS live in the stylesheets, not in the page that links the font.
    # Asking each HTML file whether IT mentions a generic family reported "no
    # fallback" on every page of a course whose CSS ends every stack in one -
    # 346 false failures on this gate's first run.
    ends_generic = False
    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            if os.path.splitext(f)[1].lower() in (".css", ".html", ".htm"):
                if any(fam in read_text(f) for fam in GENERIC_FAMILIES):
                    ends_generic = True
                    break
        if ends_generic:
            break

    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            if os.path.splitext(f)[1].lower() not in (".html", ".htm"):
                continue
            r = rel(repo, f)
            txt = read_text(f)
            for rx, kind in ((REMOTE_SCRIPT, "script"), (REMOTE_STYLE, "stylesheet")):
                for m in rx.finditer(txt):
                    host = m.group(2).split("/")[0].lower()
                    line = txt.count("\n", 0, m.start()) + 1
                    if host.endswith(font_hosts):
                        out.append(Finding(
                            "offline", WARN if ends_generic else FAIL, r, line,
                            f"remote web font from {host}. "
                            + ("this course's stacks end in a generic family, so it degrades by choice offline."
                               if ends_generic else
                               "No generic family in the stack - offline this page has no chosen fallback.")))
                    else:
                        out.append(Finding("offline", FAIL, r, line,
                                           f"remote {kind} from {host}: the page needs a network to work"))


# ------------------------------------------------------------------- 5 addresses
def check_addresses(repo: str, plat: dict, sets: dict, out: list) -> None:
    rules = plat["safety_rules"]["addresses"]
    pats = [re.compile(p) for p in rules["patterns"]]
    testonly = [re.compile(p) for p in rules["test_only_path_patterns"]]
    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            if os.path.splitext(f)[1].lower() not in TEXT_EXT:
                continue
            r = rel(repo, f)
            is_test = any(t.search(r) for t in testonly)
            txt = read_text(f)
            for rx in pats:
                m = rx.search(txt)
                if m:
                    out.append(Finding(
                        "addresses", WARN if is_test else FAIL, r,
                        txt.count("\n", 0, m.start()) + 1,
                        ("test-only page (excluded from production flavours): " if is_test
                         else "a developer machine address in content that ships: ")
                        + m.group(0)[:60]))
                    break


# ------------------------------------------------------------------------ 6 junk
def check_junk(repo: str, plat: dict, sets: dict, out: list) -> None:
    """Everything under an asset root is packaged into the APK. A .bak file is
    shipped course material that nobody reviewed."""
    pats = [re.compile(p, re.I) for p in plat["safety_rules"]["junk_patterns"]]
    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            base = os.path.basename(f)
            if any(p.search(base) for p in pats):
                out.append(Finding("junk", FAIL, rel(repo, f), 0,
                                   "editor/backup state inside an asset tree - it is packaged into the APK"))


# ---------------------------------------------------------------------- 7 assets
REF = re.compile(r"""(?:src|href)\s*=\s*["']([^"'#?>]+)""", re.I)
URLF = re.compile(r"""url\(\s*["']?([^"')#?]+)""", re.I)
PSEUDO = ("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:", "about:", "blob:")


def merged_view(repo: str, plat: dict) -> dict:
    """A map of MERGED asset path -> real file on disk.

    Gradle merges the flavour source sets into one asset root, so at runtime
    training_terminal/ and instructor_terminal/ are siblings and a link from
    one to the other is written relative to that merged root. Resolving such a
    link inside the split source tree marks a CORRECT link dead - this check
    reported 140 dead links on a tree whose real count is zero before it was
    written this way. The platform's own guide calls this out as the trap that
    wastes an afternoon.
    """
    view = {}
    for src_root in plat["flavours"]["instructor"]["assets"]:      # both source sets
        base = os.path.join(repo, src_root.replace("/", os.sep))
        if not os.path.isdir(base):
            continue
        for f in walk(base):
            view[os.path.relpath(f, base).replace("\\", "/").lower()] = f
    return view


def merged_path_of(repo: str, plat: dict, real: str) -> str | None:
    for src_root in plat["flavours"]["instructor"]["assets"]:
        base = os.path.join(repo, src_root.replace("/", os.sep))
        try:
            common = os.path.commonpath([os.path.abspath(real), os.path.abspath(base)])
        except ValueError:
            continue
        if os.path.abspath(common) == os.path.abspath(base):
            return os.path.relpath(real, base).replace("\\", "/")
    return None


def check_assets(repo: str, plat: dict, sets: dict, out: list, simulate: bool) -> None:
    """Every LOCAL file a published page points at must exist IN THE MERGED
    ROOT. References built in JavaScript are counted and skipped, never
    guessed at: several pages assemble a src from a variable, and a static
    reader that invents the value reports a file nobody ever asked for."""
    view = merged_view(repo, plat)
    skipped = 0
    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            if os.path.splitext(f)[1].lower() not in (".html", ".htm", ".css"):
                continue
            here = merged_path_of(repo, plat, f)
            if here is None:
                continue
            txt = read_text(f)
            for rx in (REF, URLF):
                for m in rx.finditer(txt):
                    target = m.group(1).strip()
                    tail = txt[m.end(1): m.end(1) + 12].lstrip("\"' )")
                    built = tail.startswith("+") or target.endswith("/")
                    if (not target or target.lower().startswith(PSEUDO) or built
                            or "'" in target or '"' in target
                            or "${" in target or "+" in target or "<" in target):
                        skipped += 1
                        continue
                    merged = os.path.normpath(
                        os.path.join(os.path.dirname(here), target)
                    ).replace("\\", "/").lower()
                    if merged in view or (merged + "/index.html") in view:
                        continue
                    out.append(Finding("assets", FAIL, rel(repo, f),
                                       txt.count("\n", 0, m.start()) + 1,
                                       "missing in the merged asset root: " + target))
    if skipped:
        out.append(Finding("assets", "NOTE", "-", 0,
                           f"{skipped} reference(s) skipped as remote or built in JavaScript"))
    if simulate:
        out.append(Finding("assets", FAIL, "SIMULATED/page.html", 12,
                           "SIMULATED missing asset (--simulate-missing-asset)"))


# ---------------------------------------------------------------------- 8 rights
def check_rights(repo: str, plat: dict, sets: dict, out: list) -> None:
    """A figure's own metadata can say it is not cleared for publication. That
    is a licensing fact about the file, and pushing it to a shared repository
    is a distribution decision a human has to make knowingly."""
    deny = [re.compile(p, re.I) for p in plat["safety_rules"]["rights"]["not_cleared_patterns"]]
    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            if os.path.basename(f) not in ("_figure_meta.json", "_photo_meta.json", "_sim_meta.json"):
                continue
            try:
                meta = json.loads(read_text(f))
            except ValueError:
                out.append(Finding("rights", WARN, rel(repo, f), 0, "asset metadata is not valid JSON"))
                continue
            if not isinstance(meta, dict):
                continue
            for key, val in meta.items():
                blob = json.dumps(val) if not isinstance(val, str) else val
                if any(d.search(blob) for d in deny):
                    out.append(Finding("rights", WARN, rel(repo, f), 0,
                                       f"'{key}' is marked not cleared for publication - a human decides "
                                       "whether it may go to the shared repository"))


# -------------------------------------------------------------------- the runner
# ------------------------------------------------------------------- 9 runtime
RUNTIME_RULES = [
    # (regex, verdict, why) - matched against HTML and JS that ships
    (re.compile(r'target\s*=\s*["\']_blank["\']', re.I), FAIL,
     'target="_blank" opens nothing in the tablet WebView - there are no tabs, so the '
     "trainee taps and the page sits there"),
    (re.compile(r"\bwindow\.open\s*\("), FAIL,
     "window.open() opens nothing in the tablet WebView - there is no window manager"),
    (re.compile(r"""["'(]\s*file:///"""), FAIL,
     "an absolute file:/// address - it resolves to nothing on a tablet"),
    (re.compile(r"""["'(]\s*[A-Za-z]:[\\/]"""), FAIL,
     "an absolute Windows path - it is the author's machine, not the tablet"),
    (re.compile(r'(?:src|href)\s*=\s*["\']/(?!/)'), FAIL,
     "a root-relative URL (/...) - the WebView serves the course from an asset "
     "sub-path, so a leading slash leaves the course"),
    (re.compile(r"\bfetch\s*\("), FAIL,
     "fetch() - a browser blocks it for a local file, so the course cannot be reviewed "
     "by opening it, and an offline tablet has nothing to fetch from"),
    (re.compile(r"\bnew\s+XMLHttpRequest\b"), FAIL,
     "XMLHttpRequest - a browser blocks it for a local file"),
    (re.compile(r'<script[^>]+type\s*=\s*["\']module["\']', re.I), FAIL,
     "an ES module - a browser blocks it for a local file"),
]

# PLATFORM code may talk to the classroom backend; COURSE content may not.
#
# That is the line, and it is not a list of filenames. The terminal shell, the live-class
# dashboard and the local-live test pages exist precisely to reach Supabase or the
# classroom laptop, and MainActivity passes exactly those hosts through. A course's own
# pages must work with no network at all - a classroom may have none, and a colleague
# reviewing the course by opening a file has none either.
#
# So: a file sitting AT a terminal root, or under live/ or local_live/, is platform.
# Anything deeper - modules/, courses/, tasks/, handout/ - is course content and is checked.
LIVE_AREAS = re.compile(r"(^|/)(live|local_live)/")


def _is_platform_file(repo: str, plat: dict, path: str) -> bool:
    p = rel(repo, path).replace(os.sep, "/")
    if LIVE_AREAS.search(p):
        return True
    for root in plat["asset_roots"].values():
        r = str(root).replace(os.sep, "/").rstrip("/")
        if p.startswith(r + "/"):
            tail = p[len(r) + 1:]
            # one segment past a terminal root = the shell itself
            if tail.count("/") <= 1:
                return True
    return False


def check_runtime(repo: str, plat: dict, sets: dict, out: list) -> None:
    """Does this course run in the two places it has to - the tablet WebView, and a
    colleague's browser opening a file?

    Every rule here is something that fails SILENTLY. A target="_blank" does not raise;
    it simply does nothing, and the report from the classroom is "the tablet froze".
    """
    backs = 0
    pages = 0
    for root in sets["trainee"] + sets["instructor"]:
        for f in walk(root):
            ext = os.path.splitext(f)[1].lower()
            if ext not in (".html", ".htm", ".js"):
                continue
            r = rel(repo, f)
            if _is_platform_file(repo, plat, f):
                continue
            txt = read_text(f)
            body = re.sub(r"<!--.*?-->", " ", txt, flags=re.S)
            body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
            body = re.sub(r"(?m)^\s*//.*$", " ", body)
            for rx, verdict, why in RUNTIME_RULES:
                m = rx.search(body)
                if m:
                    out.append(Finding("runtime", verdict, r,
                                       body.count("\n", 0, m.start()) + 1, why))
            if ext in (".html", ".htm") and _is_page(txt):
                pages += 1
                if "gbt-topback" in txt or "gb-home" in txt or "gbn-back" in txt:
                    backs += 1

    # A page a trainee can enter and not leave is the worst of these, so it is counted
    # rather than pattern-matched: the question is how many pages have no way back.
    if pages and backs < pages:
        out.append(Finding(
            "runtime", WARN, "(%d of %d pages)" % (pages - backs, pages), 0,
            "no Back affordance found (a.gbt-topback / .gbn-back / #gb-home). Hardware "
            "Back clicks that element; a page without one is a page a trainee can enter "
            "and not leave"))


def _is_page(txt: str) -> bool:
    """A fragment is markup pasted into a page, not a page - it has no Back of its own."""
    head = txt[:2000].lower()
    return "<!doctype" in head or "<html" in head or "<body" in head


def run(a) -> int:
    repo = os.path.abspath(a.repo)
    plat = load_platform(a.platform)
    sets = course_file_sets(repo, plat, a.course_id)
    out: list[Finding] = []

    meta = check_identity(repo, plat, a.course_id, sets, out)
    counts = check_roles(repo, plat, sets, out, a.simulate_leak)
    check_secrets(repo, plat, sets, out)
    check_offline(repo, plat, sets, out)
    check_addresses(repo, plat, sets, out)
    check_junk(repo, plat, sets, out)
    check_assets(repo, plat, sets, out, a.simulate_missing_asset)
    check_rights(repo, plat, sets, out)
    check_runtime(repo, plat, sets, out)

    # ---- accepted debt -------------------------------------------------
    # A finding recorded in the baseline is downgraded to a warning and says
    # so, loudly, in every report. A finding NOT in the baseline fails. This
    # is what lets a real platform with real history publish at all, without
    # any of its history becoming invisible. --strict ignores the file.
    baselined = 0
    if not a.strict and a.baseline and os.path.isfile(a.baseline):
        with open(a.baseline, "r", encoding="utf-8") as fh:
            known = json.load(fh).get("findings", [])
        index = {(k.get("check"), k.get("path")): k for k in known}
        for f in out:
            if f.level != FAIL:
                continue
            hit = index.get((f.check, f.path))
            if hit:
                f.level = WARN
                f.detail = ("KNOWN, accepted 2026-09-08 - " + f.detail
                            + " | fix: " + str(hit.get("fix", "not recorded")))
                baselined += 1

    if a.strict:
        for f in out:
            if f.level == WARN:
                f.level = FAIL

    fails = [f for f in out if f.level == FAIL]
    warns = [f for f in out if f.level == WARN]
    verdict = FAIL if fails else (WARN if warns else PASS)

    if not a.quiet:
        print("=" * 72)
        print(f"PUBLICATION GATE - course '{a.course_id}' ({sets['layout']} layout)")
        print("=" * 72)
        print(f"  trainee dirs     {[rel(repo, d) for d in sets['trainee']] or '(none)'}")
        print(f"  instructor dirs  {[rel(repo, d) for d in sets['instructor']] or '(none)'}")
        print(f"  files by role    " + ", ".join(f"{k}={v}" for k, v in counts.items()))
        for level in (FAIL, WARN, "NOTE"):
            group = [f for f in out if f.level == level]
            if group:
                print(f"\n{level} ({len(group)}):")
                for f in group[:60]:
                    print("  " + str(f))
                if len(group) > 60:
                    print(f"  ... and {len(group) - 60} more")
        print("\n" + "-" * 72)
        print("VERDICT: " + verdict
              + ("  - publication stops here" if verdict == FAIL else
                 "  - publishable; read the warnings" if verdict == WARN else
                 "  - clear to publish"))

    report = {
        "verdict": verdict, "course_id": a.course_id, "layout": sets["layout"],
        "course": meta, "role_counts": counts,
        "trainee_paths": [rel(repo, d) for d in sets["trainee"]],
        "instructor_paths": [rel(repo, d) for d in sets["instructor"]],
        "failures": [str(f) for f in fails], "warnings": [str(f) for f in warns],
        "findings": [f.as_dict() for f in out],
        "strict": bool(a.strict), "baselined": baselined,
    }
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
        if not a.quiet:
            print("report written to " + a.report)
    return 0 if verdict != FAIL else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--course-id", required=True)
    ap.add_argument("--platform", default=PLATFORM)
    ap.add_argument("--baseline", default=BASELINE,
                    help="accepted pre-existing findings; ignored under --strict")
    ap.add_argument("--report")
    ap.add_argument("--strict", action="store_true", help="every WARN becomes a FAIL")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--simulate-leak", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--simulate-missing-asset", action="store_true", help=argparse.SUPPRESS)
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
