# -*- coding: utf-8 -*-
"""test_cf_timing - CF_TIMING writes one line per run, and nothing without it (2.61.0).

    python test_cf_timing.py
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cf_timing  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:400]) if detail and not ok else ""))


def main():
    tmp = tempfile.mkdtemp(prefix="cf_timing_t_")
    path = os.path.join(tmp, "t.jsonl")
    os.environ.pop("CF_TIMING", None)
    cf_timing.note("x", "y", 1.0)
    check("without CF_TIMING nothing is written", not os.path.exists(path))
    os.environ["CF_TIMING"] = path
    try:
        ts = [threading.Thread(target=lambda k=k: [cf_timing.note("drawing_check", "page %d" % k, 0.5, virt=1000) for _ in range(20)])
              for k in range(4)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        cf_timing.note("run_audits", "1280x800 whole", 2.0, virt=None)
        rows = [json.loads(x) for x in io.open(path, encoding="utf-8")]
        check("one whole line per run, from four threads at once (81)", len(rows) == 81 and all("wall" in r and "pid" in r for r in rows), len(rows))
        s = cf_timing.summary(path)
        check("the summary adds up real seconds and the page clock per tool",
              "drawing_check" in s and " 80 " in s and "40.0" in s and "80.0" in s and "run_audits" in s, s)
    finally:
        os.environ.pop("CF_TIMING", None)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
