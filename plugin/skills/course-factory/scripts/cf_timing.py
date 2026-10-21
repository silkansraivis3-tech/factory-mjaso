# -*- coding: utf-8 -*-
"""cf_timing - where a build's seconds go, measured inside the runners (2.61.0).

    set CF_TIMING=<file.jsonl>      every hidden-browser run of a build writes one line there
    python cf_timing.py <file.jsonl>    the lines added up: per tool, real seconds and the page's own clock

WHY (2026-10-21): a build takes 40-160 s on a quiet PC and a cold hidden Chrome starts in 0.65 s, so the time is the
work inside the pages - but the drawing check and the audits run under --virtual-time-budget (their waits cost no real
time unless the page keeps Chrome busy), and review_sheets.mjs drives the real clock. Each line says both: "wall" (real
seconds the run took) and "virt" (the page's own clock at the end, ms - virtual time where a budget runs it), so a
wait that costs real time is seen. Without CF_TIMING nothing is written and nothing is slower.
"""
from __future__ import annotations

import io
import json
import os
import sys
import threading
import time

_lock = threading.Lock()


def note(tool, what, wall, **kw):
    """one line: tool, what it ran (a page, a slice, a viewport), real seconds, and anything else (virt=ms, n=slides)"""
    path = os.environ.get("CF_TIMING")
    if not path:
        return
    rec = dict(tool=tool, what=what, wall=round(wall, 3), at=round(time.time(), 3), pid=os.getpid())
    rec.update(kw)
    try:
        with _lock, io.open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def summary(path):
    """per tool: runs, real seconds, the page clock's seconds - the lines of one or more builds added up"""
    rows = {}
    for line in io.open(path, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        t = rows.setdefault(r.get("tool", "?"), [0, 0.0, 0.0])
        t[0] += 1
        t[1] += r.get("wall") or 0
        t[2] += (r.get("virt") or 0) / 1000.0
    out = ["%-28s %5s %9s %11s" % ("tool", "runs", "real s", "page clock s")]
    out += ["%-28s %5d %9.1f %11.1f" % (k, v[0], v[1], v[2]) for k, v in sorted(rows.items(), key=lambda kv: -kv[1][1])]
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    print(summary(sys.argv[1]))
