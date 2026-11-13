# -*- coding: utf-8 -*-
"""test_commons - Wikimedia Commons searched and downloaded with the factory's own User-Agent and record.

    python -I test_commons.py

No network: commons.urlopen is replaced by a stand-in that keeps every request and answers as the Commons API does.
Pinned: every request carries the tool's User-Agent with the organisation's website and no '@' anywhere - header, URL or
parameters; a request with an e-mail address in it is refused before it is sent; requests are a second apart and the API's
carry maxlag; a 429 is waited out once; search marks an NC licence not usable; get downloads the original (not a preview)
and writes a record the factory's photo checks read (credit, rights), keeps what a person wrote, and refuses NC / ND,
no licence and a file under 800 px.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import commons  # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "\n        " + str(detail)[:600]))


def page(title, licence, w=2400, h=1600, artist='<a href="//commons.wikimedia.org/wiki/User:Wf">Wolfgang Fricke</a>'):
    name = title.split(":", 1)[1].replace(" ", "_")
    return {"title": title, "index": 1, "imageinfo": [{
        "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/" + name, "descriptionurl": "https://commons.wikimedia.org/wiki/" + name,
        "width": w, "height": h, "mime": "image/jpeg", "extmetadata": {
            "ObjectName": {"value": title[5:].rsplit(".", 1)[0]}, "Artist": {"value": artist},
            "LicenseShortName": {"value": licence}, "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/3.0"},
            "DateTimeOriginal": {"value": "2014-08-04"}}}]}


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class Commons:
    """stands in for the network: keeps each request, answers the API from `pages`, a file with bytes"""

    def __init__(self, pages, busy=0):
        self.pages, self.busy, self.sent = pages, busy, []

    def __call__(self, req, timeout=60):
        self.sent.append(req)
        if self.busy:
            self.busy -= 1
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {"Retry-After": "2"}, None)
        url = req.full_url
        if url.startswith(commons.API):
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            got = [p for p in self.pages if "titles" not in q or p["title"] == q["titles"]] or [{"title": q.get("titles"), "missing": True}]
            return Answer(json.dumps({"query": {"pages": got}}).encode("utf-8"))
        return Answer(b"\xff\xd8\xff\xd9 the original file")


def main():
    tmp = tempfile.mkdtemp(prefix="commons_")
    slept, real_open, real_sleep = [], commons.urlopen, commons.time.sleep
    commons.time.sleep = lambda s: slept.append(s)
    commons.LAST = os.path.join(tmp, "last_request")
    try:
        net = Commons([page("File:Arctic Princess Hammerfest.jpg", "CC BY 3.0"), page("File:Mozah.jpg", "CC BY-NC 2.0")])
        commons.urlopen = net
        found = commons.search("Arctic Princess LNG")
        check("search: each file with its size, licence, author (its link's words) and page; an NC licence is not usable",
              [c["file"] for c in found] == ["File:Arctic Princess Hammerfest.jpg", "File:Mozah.jpg"]
              and found[0]["author"] == "Wolfgang Fricke" and found[0]["rights"] == ("ATTRIBUTION_REQUIRED", True, True)
              and found[1]["rights"] is None, found)
        folder = os.path.join(tmp, "module01", "assets", "img")
        code, lines = commons.get("File:Arctic Princess Hammerfest.jpg", folder, found_for="M01 s06")
        meta = json.load(open(os.path.join(folder, "_photo_meta.json"), encoding="utf-8"))
        rec = meta.get("arctic_princess_hammerfest.jpg") or {}
        check("get: the original file (upload.wikimedia.org, not a /thumb/ preview) and its record beside it",
              code == 0 and os.path.isfile(os.path.join(folder, "arctic_princess_hammerfest.jpg"))
              and net.sent[-1].full_url.startswith("https://upload.wikimedia.org/") and "/thumb/" not in net.sent[-1].full_url, lines)
        check("... the record as the factory's photo records are: source, page, author, licence, rights, size, the slot",
              rec.get("source") == "Wikimedia Commons" and rec.get("url_or_origin", "").startswith("https://commons.wikimedia.org/wiki/")
              and rec.get("author") == "Wolfgang Fricke" and rec.get("licence") == "CC BY 3.0"
              and rec.get("rights_state") == "ATTRIBUTION_REQUIRED" and rec.get("attribution_required") is True
              and rec.get("orig_size") == "2400x1600 px" and rec.get("found_for") == "M01 s06" and "visually_verified" not in rec, rec)
        check("... and says what the person who opens it still writes - visually_verified in words, never claimed by the script",
              "description, shows, teaching_purpose, visually_verified" in lines[-1] and "yes - <what you saw>" in lines[-1], lines)
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-factory", "compile", "scripts"))
        import compile_module as cm
        check("... its credit line names the author, the source and the licence (CC BY)",
              cm.credit_line(rec) == "Photo: Arctic Princess Hammerfest · Wolfgang Fricke · Wikimedia Commons · CC BY 3.0"
              and cm.credit_authors(rec) == ["Wolfgang Fricke"], cm.credit_line(rec))

        sent = [(r.full_url, dict(r.header_items())) for r in net.sent]
        check("every request carries the tool's User-Agent naming the organisation's website - no '@' in a header or a URL",
              sent and all(h.get("User-agent") == commons.USER_AGENT for _, h in sent) and "novikontas.org" in commons.USER_AGENT
              and not any("@" in u or "@" in "".join(h.values()) or "%40" in u for u, h in sent), sent)
        check("... the API's with maxlag=5; requests one second apart", all("maxlag=5" in u for u, _ in sent if u.startswith(commons.API))
              and slept and all(0 < s <= commons.GAP for s in slept), (sent, slept))
        try:
            commons.request(commons.API, {"action": "query", "contact": "someone@example.com"})
            refused = False
        except ValueError:
            refused = True
        check("a request with an e-mail address in it is refused before it is sent", refused and len(net.sent) == len(sent))

        meta["arctic_princess_hammerfest.jpg"].update(description="An LNG carrier with four spheres.", visually_verified="yes - x 2026-11-11")
        open(os.path.join(folder, "_photo_meta.json"), "w", encoding="utf-8").write(json.dumps(meta))
        commons.get("File:Arctic Princess Hammerfest.jpg", folder)
        rec = json.load(open(os.path.join(folder, "_photo_meta.json"), encoding="utf-8"))["arctic_princess_hammerfest.jpg"]
        check("a second download keeps what a person wrote in the record", rec.get("description") == "An LNG carrier with four spheres."
              and rec.get("visually_verified") == "yes - x 2026-11-11" and rec.get("found_for") == "M01 s06", rec)

        for title, lic, w, why in (("File:Mozah.jpg", "CC BY-NC 2.0", 2400, "not one the factory can use"),
                                   ("File:Nd.jpg", "CC BY-ND 4.0", 2400, "not one the factory can use"),
                                   ("File:None.jpg", "", 2400, "none named"),
                                   ("File:Small.jpg", "CC0", 640, "only 640 x 426 px")):
            commons.urlopen = Commons([page(title, lic, w, int(w / 1.5))])
            code, lines = commons.get(title, os.path.join(tmp, "refused"))
            check("refused, nothing downloaded: %s" % (lic or "no licence") + (" at %d px" % w if w < 800 else ""),
                  code == 1 and why in lines[0] and not os.path.isdir(os.path.join(tmp, "refused")), lines)
        commons.urlopen = Commons([page("File:Pd.jpg", "Public domain", artist="U.S. Coast Guard")])
        commons.get("File:Pd.jpg", folder)
        commons.urlopen = Commons([page("File:Gfdl.jpg", "GFDL")])
        commons.get("File:Gfdl.jpg", folder)
        meta = json.load(open(os.path.join(folder, "_photo_meta.json"), encoding="utf-8"))
        check("public domain is PUBLIC_DOMAIN with no credit asked; a licence it does not know is RIGHTS_REVIEW_REQUIRED",
              meta["pd.jpg"]["rights_state"] == "PUBLIC_DOMAIN" and meta["pd.jpg"]["attribution_required"] is False
              and meta["gfdl.jpg"]["rights_state"] == "RIGHTS_REVIEW_REQUIRED", meta)
        busy = Commons([page("File:Pd.jpg", "Public domain")], busy=1)
        commons.urlopen, slept[:] = busy, []
        found = commons.search("tank")
        check("a 429 is waited out as its Retry-After says, then asked once more", len(found) == 1 and 2 in slept
              and len(busy.sent) == 2, (slept, busy.sent))
        commons.urlopen = Commons([])
        code, lines = commons.get("File:Nowhere.jpg", folder)
        check("a file Commons does not hold is said", code == 1 and "is not a file on Wikimedia Commons" in lines[0], lines)
        plugin = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        utm = {"file": "File:Gas tanker in Forth.jpg",
               "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Gas_tanker_in_Forth.jpg"
                      "?utm_source=commons.wikimedia.org&utm_campaign=imageinfo&utm_content=original"}
        check("the saved file keeps its picture extension when the address carries a query (the factory trial saved "
              "\".org&utm_campaign=...\" files)",
              commons.file_name(utm) == "gas_tanker_in_forth.jpg" and commons.file_name(utm, "s04_tanker") == "s04_tanker.jpg"
              and commons.file_name(utm, "s04_tanker.png") == "s04_tanker.png"
              and commons.file_name(utm, "lng.carrier_v2") == "lng.carrier_v2.jpg",
              [commons.file_name(utm), commons.file_name(utm, "s04_tanker"), commons.file_name(utm, "lng.carrier_v2")])
        briefs = {p: io.open(os.path.join(plugin, *p.split("/")), encoding="utf-8").read() for p in (
            "agents/visual-sourcer.md", "skills/course-factory/SKILL.md", "skills/course-visuals/source/GUIDE.md",
            "skills/course-factory/compile/BUILDER_CARD.md", "skills/course-factory/orchestration/workflows/build_course.js")}
        check("every brief that sends a helper to Commons names commons.py, and says a request never carries a person's e-mail",
              all("commons.py" in t and "e-mail address" in t for t in briefs.values()),
              [p for p, t in briefs.items() if "commons.py" not in t or "e-mail address" not in t])
    finally:
        commons.urlopen, commons.time.sleep = real_open, real_sleep
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
