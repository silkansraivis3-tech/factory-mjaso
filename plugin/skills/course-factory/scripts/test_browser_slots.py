# -*- coding: utf-8 -*-
"""test_browser_slots - the computer-wide pool of hidden browsers (browser_slots.py / browser_slots.mjs, 2.57.0).

Proves: two processes (four threads each) never hold more slots at once than CF_BROWSER_SLOTS, and do run side by
side up to it; a slot left by a process that was killed is reclaimed; one whose PID is running but was not touched for
5 minutes is reclaimed, one touched just now is not; a thread asking again gets its own slot back (no waiting on
itself); Node (review_sheets.mjs, perf3d.mjs) waits in the same queue as Python. Every run uses a private pool folder
(CF_BROWSER_SLOT_DIR), never the real one.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import browser_slots  # noqa: E402

SKILLS = os.path.dirname(os.path.dirname(HERE))
MJS = os.path.join(SKILLS, "course-module-ux", "measure", "scripts", "browser_slots.mjs")
FAILS = []

WORKER = r"""
import json, os, sys, threading, time
sys.path.insert(0, %(here)r)
import browser_slots
out = []
def one():
    for _ in range(4):
        with browser_slots.slot():
            t_in = time.time()
            held = len([f for f in os.listdir(browser_slots.folder()) if f.startswith("slot_")])
            time.sleep(0.25)
            out.append((t_in, time.time(), held))
ts = [threading.Thread(target=one) for _ in range(4)]
[t.start() for t in ts]
[t.join() for t in ts]
print(json.dumps(out))
"""


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "   -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def most_at_once(spans):
    ev = sorted([(a, 1) for a, b, _ in spans] + [(b, -1) for a, b, _ in spans], key=lambda e: (e[0], e[1]))
    n = top = 0
    for _, d in ev:
        n += d
        top = max(top, n)
    return top


def main():
    pool = tempfile.mkdtemp(prefix="cf_slots_test_")
    env = dict(os.environ, CF_BROWSER_SLOTS="3", CF_BROWSER_SLOT_DIR=pool)
    os.environ["CF_BROWSER_SLOT_DIR"] = pool
    try:
        # 1 - two processes, four threads each, three slots
        code = WORKER % {"here": HERE}
        ps = [subprocess.Popen([sys.executable, "-I", "-c", code], env=env, stdout=subprocess.PIPE, text=True) for _ in range(2)]
        spans = []
        for p in ps:
            o, _ = p.communicate(timeout=120)
            spans += [tuple(x) for x in json.loads(o)]
        check("two processes ran all 32 browser turns", len(spans) == 32, len(spans))
        top = most_at_once(spans)
        check("two processes never held more than CF_BROWSER_SLOTS=3 at once (most at once: %d)" % top, top <= 3, top)
        check("and they did run side by side up to it (not one at a time)", top == 3, top)
        check("no holder ever saw more than 3 slot files", max(h for _, _, h in spans) <= 3, max(h for _, _, h in spans))
        check("every slot was freed afterwards", browser_slots.held() == [], browser_slots.held())

        os.environ["CF_BROWSER_SLOTS"] = "1"
        lock = os.path.join(pool, "slot_0.lock")

        # 2 - a process killed while it held a slot: its PID is not running, the slot is reclaimed
        p = subprocess.Popen([sys.executable, "-I", "-c", "import sys, time; sys.path.insert(0, %r); import browser_slots, os\n"
                              "with browser_slots.slot():\n    print('held', flush=True); time.sleep(60)" % HERE],
                             env=dict(env, CF_BROWSER_SLOTS="1"), stdout=subprocess.PIPE, text=True)
        check("a child process took the only slot", p.stdout.readline().strip() == "held")
        p.kill()
        p.wait()
        check("its lock file is left behind by the kill", os.path.isfile(lock))
        os.utime(lock, (time.time() - 5, time.time() - 5))
        t0 = time.time()
        with browser_slots.slot():
            took = time.time() - t0
        check("the killed process's slot is reclaimed at once (%.1f s)" % took, took < 3, took)

        # 3 - a running PID that stopped touching its slot 5 minutes ago (a reused PID): reclaimed; touched now: not
        io_write(lock, "%d\n" % os.getppid())
        os.utime(lock, (time.time() - browser_slots.STALE - 5,) * 2)
        check("a slot of a running PID not touched for 5 minutes is stale", browser_slots.stale(lock))
        io_write(lock, "%d\n" % os.getppid())
        os.utime(lock, (time.time() - 10,) * 2)
        check("a slot of a running PID touched 10 s ago is held", not browser_slots.stale(lock)
              and browser_slots._take(pool, 1) is None)
        os.remove(lock)

        # 4 - re-entrant: a thread that holds the only slot and asks again does not wait on itself
        t0 = time.time()
        with browser_slots.slot() as a:
            with browser_slots.slot() as b:
                same = a == b
        check("a thread asking again gets its own slot back, without waiting", same and time.time() - t0 < 1)
        check("and it is freed once, at the outer end", browser_slots.held() == [])

        # 5 - Node waits in the same queue: Python holds the only slot for 2 s, Node gets it after
        node = shutil.which("node")
        if not node:
            check("node is on this computer (review_sheets.mjs, perf3d.mjs)", False, "no node")
        else:
            js = ("import { takeSlot } from %s; const t0 = Date.now(); const rel = await takeSlot();"
                  "console.log(JSON.stringify({got: Date.now() / 1000})); rel();" % json.dumps(path_uri(MJS)))
            with browser_slots.slot():
                q = subprocess.Popen([node, "--input-type=module", "-e", js], env=dict(env, CF_BROWSER_SLOTS="1"),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                time.sleep(2)
                freed = time.time()
            o, e = q.communicate(timeout=60)
            try:
                got = json.loads(o.strip().splitlines()[-1])["got"]
            except (ValueError, IndexError, KeyError):
                got = 0
            check("Node waited for the slot Python held, and got it once freed", got >= freed - 0.05, (got, freed, e[-300:]))
            check("Node freed it again", browser_slots.held() == [])
    finally:
        shutil.rmtree(pool, ignore_errors=True)
    print("%d failure(s)" % len(FAILS) if FAILS else "All browser-slot checks passed.")
    return 1 if FAILS else 0


def io_write(path, text):
    with open(path, "w", encoding="ascii") as f:
        f.write(text)


def path_uri(p):
    from pathlib import Path
    return Path(p).as_uri()


if __name__ == "__main__":
    sys.exit(main())
