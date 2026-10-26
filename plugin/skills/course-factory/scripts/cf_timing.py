# -*- coding: utf-8 -*-
"""cf_timing - where a build's seconds go, measured inside the runners (2.61.0); a module's minutes against the
gold standard - 30-40 min a module, 20 min for its fixes (2.65.0: clock_start, clock_pass, fix_line).

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


# ---------------------------------------------------------------- the gold standard (2.65.0)
# Owner, 2026-10-26: "we want to aim for 30-40 minutes per module + 20 minutes possible fixes, that is our gold standard".
# A module's clock starts when its starter build sheet is written (compile_module.py --init-build) - or at its first
# build_module.py run when the sheet came from elsewhere - and stops at its first PASS. A fix (fix.py rebuild) is timed
# on its own against the 20 minutes.
GOLD_BUILD = (30, 40)       # minutes a module, from its starter build sheet to its first PASS
GOLD_FIX = 20               # minutes for the fixes after it


def _clock_file(course, m):
    import workspace
    return workspace.claude_path(workspace.work_folder(course, create=False), "_build", "%s_clock.json" % m)


def clock_start(course, m, reset=False, since="its starter build sheet"):
    """start the module's clock - again from now when reset (a new starter build sheet); never when it already runs"""
    path = _clock_file(course, m)
    if not reset and os.path.isfile(path):
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        io.open(path, "w", encoding="utf-8").write(json.dumps({"started": time.time(), "since": since}))
    except OSError:
        pass


def clock_pass(course, m, now=None):
    """at the module's FIRST PASS: its minutes against the gold standard, one line (and kept in the clock file);
    None at a later PASS, or when no clock runs"""
    path = _clock_file(course, m)
    try:
        rec = json.load(io.open(path, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if rec.get("passed") or not rec.get("started"):
        return None
    rec["passed"] = now or time.time()
    rec["minutes"] = mins = int(round((rec["passed"] - rec["started"]) / 60.0))
    try:
        io.open(path, "w", encoding="utf-8").write(json.dumps(rec))
    except OSError:
        pass
    lo, hi = GOLD_BUILD
    verdict = ("inside the gold standard (%d-%d min a module)" % (lo, hi) if mins <= hi else
               "OVER the gold standard of %d-%d min by %d min - the stage seconds below and the build log say where it went"
               % (lo, hi, mins - hi))
    return "TIME %s: %d min from %s to its first PASS - %s" % (m, mins, rec.get("since") or "its start", verdict)


def fix_line(seconds):
    """a fix's minutes against the 20 the gold standard gives it"""
    mins = seconds / 60.0
    took = "%.0f s" % seconds if seconds < 60 else "%.0f min" % mins     # "0 min" read as broken (gas M01, 2026-10-26)
    return ("TIME: this fix took %s - inside the gold standard's %d min for fixes" % (took, GOLD_FIX) if mins <= GOLD_FIX
            else "TIME: this fix took %s - OVER the gold standard's %d min for fixes" % (took, GOLD_FIX))


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
