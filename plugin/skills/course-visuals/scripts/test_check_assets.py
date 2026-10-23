# -*- coding: utf-8 -*-
"""test_check_assets - a source-book figure ships only on a named person's decision (2.63.2, item 10, L52).

    python -I test_check_assets.py

Pinned: a book figure at RIGHTS_REVIEW_REQUIRED stays blocked; one marked OWNER_CLEARED with its source_work but no
whole cleared_by fails (the old check passed it); `check_assets.py clear` refuses without --by, --reason and
--source-work and leaves the record alone; with them it writes the clearance and the figure passes; the knowledge
base's and the old course's plain OWNER_CLEARED (no source_work, no cleared_by) is unchanged.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_assets.py")
PASS: list[str] = []
FAIL: list[str] = []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "\n        " + str(detail)[:500]))


def run(*args):
    p = subprocess.run([sys.executable, "-I", CHECK, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def record(**kw):
    base = {"source": "ITF Guideline on the IGF Code, p. 10", "rights_state": "RIGHTS_REVIEW_REQUIRED",
            "description": "A render of an LNG fuel system.", "teaching_purpose": "the fuel chain",
            "used_in": "M01 s04", "visually_verified": "yes - a render with two tanks 2026-10-22"}
    base.update(kw)
    return base


def folder(tmp, name, meta):
    d = os.path.join(tmp, name, "img")
    os.makedirs(d)
    open(os.path.join(d, "fig.jpg"), "wb").write(b"\xff\xd8\xff\xd9")
    with open(os.path.join(d, "_photo_meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"fig.jpg": meta}, fh)
    return d


def main():
    tmp = tempfile.mkdtemp(prefix="check_assets_")
    try:
        code, out = run(folder(tmp, "held", record()))
        check("a book figure at RIGHTS_REVIEW_REQUIRED stays blocked", code == 1 and "BLOCK" in out, out[-400:])

        d = folder(tmp, "claimed", record(rights_state="OWNER_CLEARED", source_work="ITF Guideline, p. 10"))
        code, out = run(d)
        check("OWNER_CLEARED with a source_work and no cleared_by fails", code == 1 and "cleared_by" in out, out[-400:])

        d = folder(tmp, "bad", record(rights_state="OWNER_CLEARED", source_work="ITF Guideline, p. 10", cleared_by="Aleksis"))
        code, out = run(d)
        check("a cleared_by without date and reason fails", code == 1 and "cleared_by" in out, out[-400:])

        d = folder(tmp, "legacy", record(rights_state="OWNER_CLEARED"))
        code, out = run(d)
        check("a plain OWNER_CLEARED (knowledge base, old course) is as it was", code == 0, out[-400:])

        d = folder(tmp, "cmd", record())
        meta_path = os.path.join(d, "_photo_meta.json")
        before = open(meta_path, encoding="utf-8").read()
        for args in (["--reason", "classroom use", "--source-work", "ITF, p. 10"],
                     ["--by", "Aleksis Vejs", "--source-work", "ITF, p. 10"],
                     ["--by", "Aleksis Vejs", "--reason", "classroom use"]):
            code, out = run("clear", d, "fig.jpg", *args)
            check("clear refuses without --by, --reason or --source-work (%s)" % args[0], code == 2, out)
        code, out = run("clear", d, "nothere.jpg", "--by", "A B", "--reason", "x", "--source-work", "y")
        check("clear refuses a file with no record", code == 2, out)
        check("... and the record is untouched by every refusal", open(meta_path, encoding="utf-8").read() == before)

        code, out = run("clear", d, "fig.jpg", "--by", "Aleksis Vejs", "--reason", "classroom use decided by NOVIKONTAS",
                        "--source-work", "ITF Guideline on the IGF Code, p. 10, Fig. 3", "--date", "2026-10-22")
        m = json.load(open(meta_path, encoding="utf-8"))["fig.jpg"]
        check("clear writes OWNER_CLEARED, cleared_by '<name>, <date> - <reason>' and the source",
              code == 0 and m["rights_state"] == "OWNER_CLEARED" and m["source_work"].endswith("Fig. 3")
              and m["cleared_by"] == "Aleksis Vejs, 2026-10-22 - classroom use decided by NOVIKONTAS" and m["credit"] == m["source_work"], m)
        code, out = run(d)
        check("... and the cleared book figure now passes check_assets", code == 0, out[-400:])
        # 2.63.3 (the 2.63.2 run, M09: a Gas Library photo record - page_url, commons_title, credit; no source, no shows)
        lib = {"commons_title": "File:4 gas monitor forensics.jpg", "page_url": "https://commons.wikimedia.org/wiki/File%3A4_gas",
               "credit": "Galatsis, own work", "author": "Galatsis", "rights_state": "ATTRIBUTION_REQUIRED",
               "description": "4 gas monitor for personal safety. Clipped on.", "teaching_purpose": "a personal monitor",
               "used_in": "M09 s08", "visually_verified": "yes - opened 2026-09-01", "library_id": "multigas_monitor_closeup"}
        d = folder(tmp, "library", lib)
        code, out = run(d, "--strict")
        check("2.63.3 a Gas Library record (its page, no 'source') passes check_assets --strict", code == 0, out[-400:])
        root = os.path.join(tmp, "gaslib", "assets")
        os.makedirs(root)
        json.dump([{"id": "multigas_monitor_closeup", "file": "assets/photos/m.jpg", "shows": ["personal 4-gas monitor"]}],
                  open(os.path.join(root, "ASSETS.json"), "w", encoding="utf-8"))
        code, out = run("normalise", d, "--library", os.path.join(tmp, "gaslib"))
        m = json.load(open(os.path.join(d, "_photo_meta.json"), encoding="utf-8"))["fig.jpg"]
        check("... normalise writes the factory's source (its page and credit) and shows (from the library's own entry)",
              code == 0 and m.get("source", "").startswith("https://commons.wikimedia.org") and "Galatsis" in m["source"]
              and m.get("shows") == ["personal 4-gas monitor"] and m["page_url"] == lib["page_url"], (out, m))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 72)
    print("%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        return 1
    print("\nA book figure is used only on a named person's recorded decision; without it, it stays blocked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
