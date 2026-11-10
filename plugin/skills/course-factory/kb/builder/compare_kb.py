#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test only: a knowledge base made by the Course KB Builder (.exe) beside one made by kb_build.py, from the same files.

    compare_kb.py <exe KNOWLEDGE_BASE> <new KNOWLEDGE_BASE> --root <the source folder the new one was made from>
                  [--course <a course folder for kb_tool search>] [--json <file>]

Prints, per source and in total: status, units, characters, chunks, the share of single-page text chunks, heading paths
that name a page, pictures, and the five search queries of the plan scored hit@5 and MRR against an oracle neither
knowledge base controls - the pages of the source files that hold every key string (PyMuPDF text of the PDF itself;
for a scanned page and for Word and PowerPoint units, the .exe's own text of that unit), accents folded. The search is
kb_tool.py search --stdout, run on each knowledge base.
"""
from __future__ import annotations

import argparse
import difflib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import lang  # noqa: E402

KB_TOOL = os.path.join(os.path.dirname(HERE), "scripts", "kb_tool.py")
QUERIES = [("H2S exposure limit", ["h2s", "ppm"]),
           ("boiling point -162 °C LNG", ["162", "boil"]),
           ("25 % LEL alarm", ["25", "lel", "alarm"]),
           ("flammable range of methane 5 15 %", ["methane", "flammab", "15"]),
           ("kuģa drošības pamatkurss stundu skaits", ["drosibas", "stund"])]
RANK = {"ok": 3, "ocr_applied": 3, "duplicate": 3, "ok_with_gaps": 2, "needs_ocr": 1, "empty": 0, "failed": 0}
NAMES_PAGE = re.compile(r"\b(page|lpp|страница)\.?\s*\d", re.I)
UNIT = re.compile(r"^##\s+(Page|Slide|Section|Image)\s+(\d+)\b([^\n]*)$", re.M)


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def chunks_of(kb):
    out = []
    with io.open(os.path.join(kb, "search_index", "chunks.jsonl"), encoding="utf-8") as f:
        for line in f:
            out.append(json.loads(line))
    return out


def slices_parse(kb):
    """Every chunk record read the way the readers read it: seek to off, read bytes, parse."""
    idx = load(os.path.join(kb, "search_index", "index.json"))
    bad = 0
    with open(os.path.join(kb, "search_index", "chunks.jsonl"), "rb") as f:
        for i, c in enumerate(idx["chunks"]):
            f.seek(c["off"])
            try:
                rec = json.loads(f.read(c["bytes"]).decode("utf-8"))
                bad += rec["chunk_id"] != c["id"] or c["i"] != i
            except ValueError:
                bad += 1
    return len(idx["chunks"]), bad


def units_text(kb, folder):
    """{(kind, number): (text, heading suffix)} from a source's document.md."""
    try:
        text = io.open(os.path.join(kb, folder, "document.md"), encoding="utf-8").read()
    except (OSError, TypeError):
        return {}
    marks = list(UNIT.finditer(text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[(m.group(1).lower(), int(m.group(2)))] = (text[m.end():end], m.group(3))
    return out


def norm(s):
    return " ".join(lang.fold(s or "").lower().split())


def oracle(exe_kb, root, man):
    """{(source_path, unit number): folded text} - PyMuPDF text of each PDF page, the .exe's text for OCR pages and
    for Word/PowerPoint units."""
    import pymupdf
    pages = {}
    for s in man["sources"]:
        if s.get("status") == "duplicate" or not s.get("output_folder"):
            continue
        units = units_text(exe_kb, s["output_folder"])
        if s["format"] == "pdf":
            try:
                doc = pymupdf.open(os.path.join(root, s["source_path"]))
            except Exception:                                 # noqa: BLE001
                continue
            for i, page in enumerate(doc, 1):
                t = page.get_text()
                u = units.get(("page", i))
                if u and "recovered by OCR" in u[1]:
                    t = u[0]
                pages[(s["source_path"], i)] = norm(t)
            doc.close()
        else:
            for (kind, n), (t, _) in units.items():
                pages[(s["source_path"], n)] = norm(t)
    return pages


def search(kb, q, course, top=12):
    p = subprocess.run([sys.executable, KB_TOOL, "search", kb, q, "--course", course, "--top", str(top), "--stdout"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    hits = []
    current = None
    for line in p.stdout.splitlines():
        m = re.match(r"^## (\d+) · (.+) — (\w+?)s? (\d+)(?:–(\d+))?$", line)
        if m:
            current = {"file": m.group(2), "p1": int(m.group(4)), "p2": int(m.group(5) or m.group(4))}
            hits.append(current)
        elif current is not None and line.startswith("`") and line.endswith("`") and "path" not in current:
            current["path"] = line.strip("`")
    return hits


def score(hits, right):
    rank = None
    for i, h in enumerate(hits[:5], 1):
        if any((h.get("path"), p) in right for p in range(h["p1"], h["p2"] + 1)):
            rank = i
            break
    seen, repeats = set(), 0
    for h in hits[:12]:
        k = (h.get("path"), h["p1"])
        repeats += k in seen
        seen.add(k)
    return {"hit5": rank is not None, "rr": (1.0 / rank) if rank else 0.0, "repeats": repeats}


def per_kb(kb):
    man = load(os.path.join(kb, "SOURCE_MANIFEST.json"))
    ch = chunks_of(kb)
    text = [c for c in ch if c["kind"] == "text"]
    page_text = [c for c in text if c["unit_kind"] == "page"]
    images_missing = 0
    for s in man["sources"]:
        if s.get("output_folder") and s.get("status") != "duplicate":
            try:
                meta = load(os.path.join(kb, s["output_folder"], "metadata.json"))
            except (OSError, ValueError):
                continue
            images_missing += sum(1 for im in meta.get("images", [])
                                  if not os.path.isfile(os.path.join(kb, s["output_folder"], "images", im.get("file") or "")))
    n, bad = slices_parse(kb)
    return {"man": man, "chunks": len(ch), "text_chunks": len(text), "table_chunks": sum(c["kind"] == "table" for c in ch),
            "image_chunks": sum(c["kind"] == "image" for c in ch),
            "single_page_share": round(sum(c["page_start"] == c["page_end"] for c in text) / max(1, len(text)), 3),
            "single_page_share_pdf": round(sum(c["page_start"] == c["page_end"] for c in page_text) / max(1, len(page_text)), 3),
            "page_named_headings": sum(1 for c in text if any(NAMES_PAGE.search(h) for h in c["heading_path"])),
            "images": sum(s.get("image_count", 0) for s in man["sources"]), "images_missing_files": images_missing,
            "units": sum(s.get("unit_count", 0) for s in man["sources"] if s.get("status") != "duplicate"),
            "chars": sum(s.get("extracted_characters", 0) for s in man["sources"]),
            "slices": n, "slices_bad": bad, "seconds": man.get("run", {}).get("seconds"),
            "statuses": {k: sum(1 for s in man["sources"] if s["status"] == k) for k in RANK}}


def table_chars(kb, s):
    try:
        meta = load(os.path.join(kb, s["output_folder"], "metadata.json"))
    except (OSError, ValueError, TypeError):
        return 0
    return sum(len(" ".join(c for row in t["cells"] for c in row)) for t in meta.get("tables", [])
               if t.get("quality") != "NEEDS_REVIEW")


def ocr_similarity(exe_kb, new_kb, se, sn):
    a, b = units_text(exe_kb, se["output_folder"]), units_text(new_kb, sn["output_folder"])
    out = []
    for k, (t, suffix) in a.items():
        if "recovered by OCR" in suffix and k in b and "recovered by OCR" in b[k][1]:
            x, y = " ".join(re.sub(r"[#*\[\]]", " ", t).split()), " ".join(re.sub(r"[#*\[\]]", " ", b[k][0]).split())
            out.append(difflib.SequenceMatcher(None, x[:4000], y[:4000], autojunk=False).ratio())
    return out


WORD3 = re.compile(r"[^\W_]{3,}", re.U)


_TOOL_LINE = re.compile(r"^(\s*$|_\[No selectable|_Grid also stored|_Stored as|_Text read from|_\(\d+ more rows|"
                        r"\*\*(Table|Image) - |\[\[|Verbatim text|interpreted\.|(page|slide|section) in the "
                        r"original|Warnings:|Reason:|No content could|`\.\./\.\./NEEDS)")


def words_of(folder):
    """Distinct words (letters and digits, three or more) of a source's CONTENT: document.md below its first unit
    heading and the table grids - not the builder's own wording (headers, table ids, warnings, engine names)."""
    out = set()
    for d, _s, files in os.walk(folder):
        for f in files:
            p = os.path.join(d, f)
            if f == "document.md" or (f.endswith(".md") and os.path.basename(d) == "tables"):
                with io.open(p, encoding="utf-8", errors="replace") as h:
                    lines = h.read().split("\n")
                if f == "document.md":
                    start = next((i for i, l in enumerate(lines) if UNIT.match(l)), len(lines))
                    lines = lines[start:]
                for l in lines:
                    if UNIT.match(l) or _TOOL_LINE.match(l) or (f != "document.md" and not l.startswith("|")):
                        continue
                    out |= {t.lower() for t in WORD3.findall(l)}
    return out


def fragment(w, have):
    """A word that is only a line-end hyphen joined differently ("bylaws" / "by-laws", "lowflashpoint"): part of a
    word the other side has, or made of words the other side has (a part of one or two letters counts)."""
    if any(len(k) > len(w) and (k.startswith(w) or k.endswith(w)) for k in have):
        return True
    for i in range(1, len(w)):
        a, b = w[:i], w[i:]
        if (a in have or len(a) <= 2) and (b in have or len(b) <= 2) and (a in have or b in have):
            return True
    return False


def coverage(exe_kb, new_kb, me, mn):
    """[(source, exe words, missing real words)]: words of the .exe's source folder the new one lacks."""
    rows = []
    for sp, se in me.items():
        sn = mn.get(sp)
        if not sn or not se.get("output_folder") or not sn.get("output_folder") or se.get("status") == "duplicate":
            continue
        we, wn = words_of(os.path.join(exe_kb, se["output_folder"])), words_of(os.path.join(new_kb, sn["output_folder"]))
        longer = {k for k in wn if len(k) > 3}
        real = sorted(w for w in we - wn if not fragment(w, longer | wn))
        rows.append((sp, len(we), real))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("exe_kb")
    ap.add_argument("new_kb")
    ap.add_argument("--root", required=True)
    ap.add_argument("--course")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    E, N = per_kb(a.exe_kb), per_kb(a.new_kb)
    me = {s["source_path"]: s for s in E["man"]["sources"]}
    mn = {s["source_path"]: s for s in N["man"]["sources"]}
    print("%-58s %-12s %-12s %11s %17s %9s %9s" % ("source", "status exe", "status new", "units e/n", "chars e/n (d%)",
                                                   "chunks", "images"))
    worse, unit_diff, char_out, sims = [], [], [], []
    for sp in sorted(set(me) | set(mn)):
        se, sn = me.get(sp), mn.get(sp)
        if not se or not sn:
            print("%-58s only in %s" % (sp[:58], "exe" if se else "new"))
            continue
        ce, cn = se.get("extracted_characters", 0), sn.get("extracted_characters", 0)
        cn_t = cn + (table_chars(a.new_kb, sn) if sn["format"] == "pdf" else 0)
        d = (cn - ce) * 100.0 / ce if ce else 0.0
        dt = (cn_t - ce) * 100.0 / ce if ce else 0.0
        print("%-58s %-12s %-12s %5d/%-5d %8d/%-8d %+5.1f%% (%+5.1f%% w/ tables) %4d/%-4d %4d/%-4d"
              % (sp[:58], se["status"], sn["status"], se.get("unit_count", 0), sn.get("unit_count", 0), ce, cn, d, dt,
                 se.get("chunk_count", 0), sn.get("chunk_count", 0), se.get("image_count", 0), sn.get("image_count", 0)))
        if RANK.get(sn["status"], 0) < RANK.get(se["status"], 0):
            worse.append(sp)
        if se.get("unit_count") != sn.get("unit_count"):
            unit_diff.append(sp)
        text_pdf = sn["format"] == "pdf" and not se.get("units_requiring_ocr") and se["status"] == "ok"
        if text_pdf and ce and abs(d) > 3:
            char_out.append((sp, round(d, 1), round(dt, 1)))
        if se["format"] == "pdf" and se.get("output_folder") and sn.get("output_folder"):
            sims += ocr_similarity(a.exe_kb, a.new_kb, se, sn)
    print()
    for name, k in (("units", "units"), ("characters", "chars"), ("chunks", "chunks"), ("text chunks", "text_chunks"),
                    ("table chunks", "table_chunks"), ("image chunks", "image_chunks"),
                    ("single-page share (text chunks)", "single_page_share"),
                    ("single-page share (PDF text chunks)", "single_page_share_pdf"),
                    ("heading paths naming a page", "page_named_headings"), ("images", "images"),
                    ("image files missing", "images_missing_files"), ("chunk slices", "slices"),
                    ("chunk slices that do not parse", "slices_bad"), ("run seconds", "seconds")):
        print("%-38s exe %-10s new %s" % (name, E[k], N[k]))
    print("%-38s exe %s\n%-38s new %s" % ("statuses", E["statuses"], "", N["statuses"]))
    sims.sort()
    print("sources worse than the exe: %s" % (worse or "none"))
    print("sources with another unit count: %s" % (unit_diff or "none"))
    print("text PDFs outside +-3%% characters: %s" % (char_out or "none"))
    if sims:
        print("OCR pages read by both: %d, similarity median %.3f, share >= 0.97: %.2f"
              % (len(sims), sims[len(sims) // 2], sum(s >= 0.97 for s in sims) / len(sims)))
    result = {"exe": {k: v for k, v in E.items() if k != "man"}, "new": {k: v for k, v in N.items() if k != "man"},
              "worse": worse, "unit_diff": unit_diff, "char_out": char_out,
              "ocr_similarity": {"n": len(sims), "median": sims[len(sims) // 2] if sims else None,
                                 "share_097": (sum(s >= 0.97 for s in sims) / len(sims)) if sims else None}}
    cov = coverage(a.exe_kb, a.new_kb, me, mn)
    total_e = sum(n for _, n, _ in cov)
    total_m = sum(len(m) for _, _, m in cov)
    print("\nword coverage: %d distinct words in the .exe's source folders, %d (%.2f%%) missing from the new ones "
          "(hyphen fragments not counted)" % (total_e, total_m, 100.0 * total_m / max(1, total_e)))
    for sp, n, miss in sorted(cov, key=lambda r: -len(r[2])):
        if miss:
            print("  %4d of %5d  %-55s e.g. %s" % (len(miss), n, sp[-55:], " ".join(miss[:14])))
    result["coverage"] = [{"source": sp, "exe_words": n, "missing": miss} for sp, n, miss in cov]
    if a.course:
        orc = oracle(a.exe_kb, a.root, E["man"])
        print("\nsearch (kb_tool.py search --stdout), hit@5 / reciprocal rank / repeated file+page in top 12:")
        rows = []
        for q, keys in QUERIES:
            right = {k for k, t in orc.items() if all(key in t for key in keys)}
            se_, sn_ = score(search(a.exe_kb, q, a.course), right), score(search(a.new_kb, q, a.course), right)
            rows.append({"query": q, "right_pages": len(right), "exe": se_, "new": sn_})
            print("  %-42s right pages %4d | exe %s %.2f %d | new %s %.2f %d" % (q, len(right), "hit " if se_["hit5"] else "miss",
                                                                             se_["rr"], se_["repeats"],
                                                                             "hit " if sn_["hit5"] else "miss",
                                                                             sn_["rr"], sn_["repeats"]))
        result["search"] = rows
    if a.json:
        with io.open(a.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
