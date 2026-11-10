# -*- coding: utf-8 -*-
"""search_index\\chunks.jsonl and search_index\\index.json - the Course Source Processor's index, version 5.

The tokenizer is a copy of the Course Source Processor's (csp/indexer.py), because kb_tool.py and fact_check.py read a
version-5 index with that same rule: letters and digits ("H2S", "CO2", "162" are terms), any script - Latin with
accents and Cyrillic alike - lower case, two characters or more, numbers up to four digits, 52 English stop words.
Each chunk is one JSON line; index.json holds its byte offset and length, so a reader seeks and reads one line.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

INDEX_VERSION = 5
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
STOPWORDS = set("""a an and are as at be been but by can for from had has have if in into is it its may must not of on or
shall should such than that the their them then there these those to was were when which will with would you your""".split())


def tokenize(text, min_length=2):
    out = []
    for m in _TOKEN.finditer((text or "").lower()):
        t = m.group(0)
        if len(t) < min_length or t in STOPWORDS or (t.isdigit() and len(t) > 4):
            continue
        out.append(t)
    return out


def chunk_record(c):
    """A chunk as chunks.jsonl holds it - the Course Source Processor's keys, in its order."""
    d = {"chunk_id": c["chunk_id"], "kind": c["kind"], "doc_id": c["doc_id"], "source_filename": c["source_filename"],
         "source_path": c["source_path"], "unit_kind": c["unit_kind"], "page_start": c["page_start"],
         "page_end": c["page_end"], "heading_path": c["heading_path"], "char_count": len(c["text"]),
         "navigational": c["navigational"]}
    if c.get("from_ocr"):
        d["from_ocr"] = True
    if c.get("asset_path"):
        d["asset_path"] = c["asset_path"]
        d["asset_id"] = c.get("asset_id")
    d["text"] = c["text"]
    return d


class IndexWriter(object):
    """Writes chunks.jsonl as chunks come and keeps the postings; close() writes index.json."""

    def __init__(self, folder, min_token_length=2):
        os.makedirs(folder, exist_ok=True)
        self.folder, self.min_len = folder, min_token_length
        self.handle = open(os.path.join(folder, "chunks.jsonl"), "wb")
        self.offset, self.total_tokens = 0, 0
        self.records, self.postings, self.documents = [], {}, {}

    def add_document(self, doc_id, info):
        self.documents[doc_id] = info

    def add(self, c):
        ordinal = len(self.records)
        data = (json.dumps(chunk_record(c), ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        self.handle.write(data)
        tokens = tokenize(" ".join(c["heading_path"]) + " " + c["text"], self.min_len)
        freq = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        for t, f in freq.items():
            self.postings.setdefault(t, []).append([ordinal, f])
        self.records.append({"i": ordinal, "id": c["chunk_id"], "doc": c["doc_id"], "file": c["source_filename"],
                             "p1": c["page_start"], "p2": c["page_end"], "h": " > ".join(c["heading_path"]),
                             "n": len(tokens), "nav": 1 if c["navigational"] else 0, "kind": c["kind"],
                             "uk": c["unit_kind"], "sp": c["source_path"], "ocr": 1 if c.get("from_ocr") else 0,
                             "asset": c.get("asset_path") or "", "aid": c.get("asset_id") or "",
                             "off": self.offset, "bytes": len(data)})
        self.total_tokens += len(tokens)
        self.offset += len(data)

    def close(self):
        self.handle.close()
        n = len(self.records)
        payload = {"index_version": INDEX_VERSION,
                   "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "chunk_count": n, "avg_tokens_per_chunk": round(self.total_tokens / n, 2) if n else 0,
                   "bm25": {"k1": 1.2, "b": 0.75, "navigational_penalty": 0.35}, "min_token_length": self.min_len,
                   "documents": self.documents, "chunks": self.records,
                   "df": {t: len(p) for t, p in self.postings.items()}, "postings": self.postings}
        with open(os.path.join(self.folder, "index.json"), "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))     # dumps: the fast encoder
        return {"chunk_count": n, "unique_terms": len(self.postings)}
