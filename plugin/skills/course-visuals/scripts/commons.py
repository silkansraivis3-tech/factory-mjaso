#!/usr/bin/env python3
"""commons.py - free photographs from Wikimedia Commons: searched, and downloaded with their record.

    commons.py search "<terms>" [--limit 12] [--json]
    commons.py get "File:<name>.jpg" <assets folder> [--name <file name>] [--found-for "M01 s06"]

search   the files Commons holds for the terms, each with its original size, licence, author and page. A licence the
         factory cannot use (NC, ND, none named) is marked "not usable".
get      the ORIGINAL file (never a preview) into the folder, and its record into the folder's _photo_meta.json: title,
         source, url_or_origin (the file's page), author, licence, licence_url, rights_state, attribution_required,
         modification_permitted, orig_size, downloaded, found_for. Refused: NC, ND or no licence named, and a file under
         800 px on its long side (the module's pre-check stops the build on it). A licence it does not know (GFDL alone,
         a permission note) is RIGHTS_REVIEW_REQUIRED - listed for the owner, never a silent ship. A record already there
         keeps every field a person wrote.
         Then open the file and look at it, and write what it shows into its record: description, shows,
         teaching_purpose and "visually_verified": "yes - <what you saw> <YYYY-MM-DD>". The script never says a picture
         was looked at.

Every request carries USER_AGENT: the tool and the organisation's public website - never a person's name, e-mail or
account, in a header, a parameter or a URL. Requests go one at a time, at most one a second from every helper on this
computer together, the API's with maxlag=5; a 429 or 503 waits as its Retry-After says, then tries once more
(Wikimedia's API etiquette and User-Agent policy).

Exit 0 done · 1 refused or nothing found · 2 bad usage or no answer from Commons.
"""
from __future__ import annotations

import argparse
import datetime
import html
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from image_size import PHOTO_FLOOR  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
SITE = "https://www.novikontas.org"
USER_AGENT = "NOVIKONTAS-course-factory-commons/1.0 (%s) python-urllib/%d.%d" % (SITE, sys.version_info[0], sys.version_info[1])
GAP = 1.0                                   # seconds between two requests, across every process on this computer
LAST = os.path.join(tempfile.gettempdir(), "novikontas_commons_last_request")
NOT_USABLE = re.compile(r"\b(NC|ND)\b|non[- ]?commercial|no[- ]?deriv", re.I)
FREE = re.compile(r"^\s*(public domain|PD\b|PD-|CC0|CC-?zero)", re.I)
CC_BY = re.compile(r"^\s*CC[ -]BY(-SA)?\b", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
IMAGE = re.compile(r"\.(jpe?g|png|tiff?|webp|gif)$", re.I)


def urlopen(req, timeout=60):
    return urllib.request.urlopen(req, timeout=timeout)


def wait_turn():
    """at most one request a second from this computer: the time of the last one is kept in a file every helper reads"""
    try:
        last = os.path.getmtime(LAST)
    except OSError:
        last = 0.0
    pause = last + GAP - time.time()
    if pause > 0:
        time.sleep(min(pause, GAP))
    try:
        with open(LAST, "w") as f:
            f.write("commons")
    except OSError:
        pass


def request(url, params=None):
    """-> the answer's bytes. One request at a time, the factory's own User-Agent, and a 429 / 503 waited out once"""
    if EMAIL.search(" ".join([url] + [str(v) for v in (params or {}).values()])):
        raise ValueError("refused - an e-mail address in a request to Commons; a request names the tool, never a person")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for attempt in (1, 2):
        wait_turn()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(req) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == 2:
                raise
            try:
                pause = int(e.headers.get("Retry-After") or 5)
            except ValueError:
                pause = 5
            time.sleep(min(max(pause, 1), 60))


def api(**params):
    params.update(format="json", formatversion="2", maxlag="5")
    return json.loads(request(API, params).decode("utf-8"))


def text_of(value):
    """the words of an extmetadata value, without its links and markup"""
    t = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", t).strip()


def rights(licence):
    """(rights_state, attribution_required, modification_permitted) for a licence name, or None when it cannot be used"""
    if not licence.strip() or NOT_USABLE.search(licence):
        return None
    if FREE.search(licence):
        return "PUBLIC_DOMAIN", False, True
    if CC_BY.search(licence):
        return "ATTRIBUTION_REQUIRED", True, True
    return "RIGHTS_REVIEW_REQUIRED", True, False


def candidate(page):
    """one file of an API answer -> what search prints and get records"""
    ii = (page.get("imageinfo") or [{}])[0]
    em = ii.get("extmetadata") or {}
    v = lambda k: text_of((em.get(k) or {}).get("value"))
    licence = v("LicenseShortName") or v("UsageTerms")
    title = page.get("title", "")
    return {"file": title, "page": ii.get("descriptionurl") or "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(
                title.replace(" ", "_")), "url": ii.get("url", ""), "mime": ii.get("mime", ""),
            "width": int(ii.get("width") or 0), "height": int(ii.get("height") or 0),
            "title": v("ObjectName") or re.sub(r"^File:|\.\w+$", "", title).replace("_", " ").strip(),
            "author": v("Artist") or v("Credit"), "licence": licence, "licence_url": v("LicenseUrl"),
            "date_original": v("DateTimeOriginal"), "rights": rights(licence)}


IINFO = {"prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
         "iiextmetadatafilter": "ObjectName|Artist|Credit|LicenseShortName|UsageTerms|LicenseUrl|DateTimeOriginal"}


def search(terms, limit=12):
    data = api(action="query", generator="search", gsrnamespace="6", gsrsearch=terms, gsrlimit=str(limit), **IINFO)
    pages = sorted((data.get("query") or {}).get("pages") or [], key=lambda p: p.get("index", 0))
    return [candidate(p) for p in pages if IMAGE.search(p.get("title", ""))]


def info(file_title):
    t = file_title if file_title.lower().startswith("file:") else "File:" + file_title
    data = api(action="query", titles=t, **IINFO)
    pages = (data.get("query") or {}).get("pages") or []
    return candidate(pages[0]) if pages and not pages[0].get("missing") and pages[0].get("imageinfo") else None


def file_name(c, name=None):
    base = name or re.sub(r"[^a-z0-9]+", "_", re.sub(r"^File:", "", c["file"], flags=re.I).rsplit(".", 1)[0].lower()).strip("_")[:60]
    ext = os.path.splitext(c["url"] or c["file"])[1].lower() or ".jpg"
    return base if os.path.splitext(base)[1] else base + ext


def get(file_title, folder, name=None, found_for=""):
    """-> (exit code, [lines]). The original file and its record, or why not"""
    c = info(file_title)
    if not c:
        return 1, ["%s is not a file on Wikimedia Commons" % file_title]
    if not c["rights"]:
        return 1, ["%s not downloaded - its licence (%s) is not one the factory can use: public domain, CC0, CC BY or "
                   "CC BY-SA. Record it as REJECTED if the next search should skip it" % (c["file"], c["licence"] or "none named")]
    if max(c["width"], c["height"]) < PHOTO_FLOOR:
        return 1, ["%s not downloaded - only %d x %d px; under %d px on its long side no enlargement makes it sharp"
                   % (c["file"], c["width"], c["height"], PHOTO_FLOOR)]
    os.makedirs(folder, exist_ok=True)
    fname = file_name(c, name)
    data = request(c["url"])
    with open(os.path.join(folder, fname), "wb") as f:
        f.write(data)
    state, attribution, modify = c["rights"]
    mp = os.path.join(folder, "_photo_meta.json")
    try:
        with io.open(mp, encoding="utf-8-sig") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        meta = {}
    rec = dict(meta.get(fname) or {})
    rec.update({"title": c["title"], "source": "Wikimedia Commons", "url_or_origin": c["page"], "author": c["author"],
                "licence": c["licence"], "licence_url": c["licence_url"], "rights_state": state,
                "attribution_required": attribution, "modification_permitted": modify,
                "orig_size": "%dx%d px" % (c["width"], c["height"]), "downloaded": datetime.date.today().isoformat()})
    if c["date_original"]:
        rec["date_original"] = c["date_original"]
    if found_for:
        rec["found_for"] = found_for
    meta[fname] = rec
    with io.open(mp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(meta, ensure_ascii=False, indent=1))
    todo = [k for k in ("description", "shows", "teaching_purpose", "visually_verified") if not rec.get(k)]
    return 0, ["Downloaded %s (%d x %d px, %s, %s) -> %s" % (c["file"], c["width"], c["height"], c["licence"], state,
                                                             os.path.join(folder, fname)),
               "Record written in %s" % mp] + (
        ["Open it and look at it, then write into its record: %s - visually_verified as \"yes - <what you saw> <YYYY-MM-DD>\""
         % ", ".join(todo)] if todo else [])


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("terms")
    s.add_argument("--limit", type=int, default=12)
    s.add_argument("--json", action="store_true")
    g = sub.add_parser("get")
    g.add_argument("file")
    g.add_argument("folder")
    g.add_argument("--name", help="the file name in the folder (default: from the Commons title)")
    g.add_argument("--found-for", default="", help="the slot it was found for, e.g. \"M01 s06\"")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "search":
            found = search(a.terms, max(1, min(a.limit, 50)))
            if a.json:
                print(json.dumps([dict(c, rights=(c["rights"] or ["NOT_USABLE"])[0]) for c in found], ensure_ascii=False, indent=1))
                return 0 if found else 1
            for c in found:
                print("%s\n    %d x %d px · %s · %s · %s\n    %s" % (
                    c["file"], c["width"], c["height"], c["licence"] or "no licence named",
                    (c["rights"] or ["not usable"])[0], c["author"][:80] or "no author named", c["page"]))
            if not found:
                print("Nothing on Commons for: %s" % a.terms)
            return 0 if found else 1
        code, lines = get(a.file, a.folder, a.name, a.found_for)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("No answer from Wikimedia Commons: %s" % e)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
