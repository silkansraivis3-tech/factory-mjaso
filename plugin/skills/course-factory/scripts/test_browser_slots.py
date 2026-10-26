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
        # 2.63.3 - one module's first build at a time: another waits its turn, at most wait_max s, then goes anyway
        import threading
        got = {}

        def first(name, hold, wait_max, pole=False):
            t = time.time()
            with browser_slots.cold_turn(wait_max, first=pole) as waited:
                got[name] = (time.time() - t, waited)
                time.sleep(hold)
        a = threading.Thread(target=first, args=("a", 2.0, 30))
        a.start()
        time.sleep(0.3)
        b = threading.Thread(target=first, args=("b", 0.1, 30))
        c = threading.Thread(target=first, args=("c", 0.1, 0.5))
        d = threading.Thread(target=first, args=("d", 0.1, 30, True))
        b.start()
        c.start()
        d.start()
        for x in (a, b, c, d):
            x.join(60)
        check("a second first build waits for the one running (%.1f s)" % got["b"][0], 1.4 <= got["b"][0] < 10, got)
        check("... and one with a short limit goes anyway when it runs out (%.1f s)" % got["c"][0], 0.4 <= got["c"][0] < 1.4, got)
        check("2.65.0 the long pole's first build (first=True) never waits (%.2f s)" % got["d"][0], got["d"][0] < 0.3, got)
        check("... the turn is freed afterwards", not os.path.exists(os.path.join(pool, "cold_build.lock")))
        foreground_part(pool)
        reuse_part(pool)
    finally:
        shutil.rmtree(pool, ignore_errors=True)
    print("%d failure(s)" % len(FAILS) if FAILS else "All browser-slot checks passed.")
    return 1 if FAILS else 0


# 2.65.0 - a page that reports what a hidden browser gives it: its window, its clock after the virtual-time budget, what it
# kept from an earlier job (storage), whether WebGL works and the scrollbar's width
PAGE = """<!DOCTYPE html><html><body style="margin:0"><div style="height:3000px"></div><script>
var gl = null; try { gl = document.createElement('canvas').getContext('webgl'); } catch (e) {}
var before = localStorage.getItem('k'); localStorage.setItem('k', 'set');
setTimeout(function () { var p = document.createElement('pre'); p.id = 'o';
  p.textContent = JSON.stringify({w: innerWidth, h: innerHeight, sb: innerWidth - document.documentElement.clientWidth,
    late: true, before: before, gl: !!gl}); document.body.appendChild(p); }, 5000);
</script></body></html>"""


def foreground_part(pool):
    """2.66.4 - the hidden Chrome's pages are never backgrounded: Chrome lowers an invisible page's renderer to Windows Idle
    priority (seen on the 2.66.3 IGF run: the kept Chromes' renderers at Idle, a figure probe 10-17 s real for ~1 s of page
    clock, ~1.2 s alone) - on a laptop with two fast cores that work goes to the slow ones. Puppeteer passes these flags on
    every launch; review_sheets.mjs and shot3d.mjs did already, the kept Chrome and the studio did not"""
    import browser_slots as bs
    args = bs.keeper_args("chrome.exe", os.path.join(pool, "prof"), ("--hide-scrollbars",))
    check("2.66.4 the kept Chrome starts with every no-background flag (%s)" % ", ".join(bs.FOREGROUND),
          all(f in args for f in bs.FOREGROUND) and "--remote-debugging-port=0" in args and args[-1] == "about:blank", args)
    cmd = ["chrome.exe", "--headless=new", "--disable-gpu", "--window-size=1296,895", "--dump-dom"] + list(bs.FOREGROUND) + ["file:///x.html"]
    check("... a probe command carrying them still runs in the kept Chrome (dom_job)", bs.dom_job(cmd) is not None, bs.dom_job(cmd))
    rec_path = os.path.join(pool, "old_keeper.json")
    io_write(rec_path, json.dumps({"pid": os.getpid(), "keeper": os.getpid(), "ws": "ws://x", "exe": "chrome.exe", "jobs": 0}))
    check("... a kept Chrome started before 2.66.4 (no \"fg\" in its record) is not used again", not bs.current(json.load(open(rec_path)), "chrome.exe"))
    check("... one started with them is", bs.current({"pid": os.getpid(), "keeper": os.getpid(), "exe": "chrome.exe", "jobs": 0,
                                                      "fg": bs.FG}, "chrome.exe"))


def reuse_part(pool):
    """one kept Chrome per slot (browser_slots.run_dom): the same answer as a fresh Chrome, nothing kept between jobs, a
    restart every CF_CHROME_JOBS jobs, a stalled page ended, the Chrome ended when idle"""
    import re
    exe = None
    for c in (os.environ.get("CF_BROWSER"), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if c and os.path.isfile(c):
            exe = c
            break
    if not exe:
        print("SKIP  the kept Chrome (no Chrome or Edge)")
        return
    tmp = tempfile.mkdtemp(prefix="cf_reuse_")
    os.environ.update(CF_BROWSER_SLOTS="1", CF_CHROME_JOBS="3", CF_CHROME_IDLE="30")
    try:
        f = os.path.join(tmp, "p.html")
        io_write(f, PAGE)
        from pathlib import Path
        n = [0]

        def cmd(*extra):                                 # a fresh Chrome gets a profile of its own each time, as the tools give it
            n[0] += 1
            return [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--user-data-dir=" + os.path.join(tmp, "prof%d" % n[0]),
                    "--window-size=1100,700", "--virtual-time-budget=8000"] + list(extra) + ["--dump-dom", Path(f).as_uri()]

        def ask(c, reuse):
            os.environ["CF_CHROME_REUSE"] = "on" if reuse else "off"
            t = time.time()
            p = browser_slots.run_dom(c, timeout=60, capture_output=True, text=True, encoding="utf-8", errors="replace")
            m = re.search(r'<pre id="o">(.*?)</pre>', p.stdout or "")
            return (json.loads(m.group(1).replace("&quot;", '"')) if m else None), time.time() - t
        check("dom_job reads a --dump-dom command; a flag it does not know is not reused",
              browser_slots.dom_job(cmd()) and browser_slots.dom_job(cmd("--hide-scrollbars"))[4] == ("--hide-scrollbars",)
              and browser_slots.dom_job(cmd("--force-device-scale-factor=2")) is None)
        own = []
        for extra in ((), ("--hide-scrollbars",), ("--disable-3d-apis",)):
            fresh, t_fresh = ask(cmd(*extra), False)
            kept1, _ = ask(cmd(*extra), True)
            kept2, t_kept = ask(cmd(*extra), True)
            own += [r for _, r in browser_slots.kept() if r and tuple(r.get("variant") or ()) == tuple(extra) and r.get("jobs") == 2]
            check("%s: a kept Chrome gives the page the same window, the budget's late timer, the same scrollbar and WebGL as a "
                  "fresh one (fresh %.2f s, kept %.2f s)" % (" ".join(extra) or "plain", t_fresh, t_kept),
                  fresh and kept1 == fresh and kept2 == fresh and fresh["late"] and fresh["before"] is None, (fresh, kept1, kept2))
        check("... nothing is kept between jobs (a new browser context: the second job sees no storage of the first)",
              kept2 and kept2["before"] is None, kept2)
        check("... one kept Chrome per flag set in the slot, each running both of its jobs",
              len(own) == 3 and len({r["pid"] for r in own}) == 3, own)
        for f_, _ in browser_slots.kept():               # start over: every kept Chrome retired
            browser_slots._retire(os.path.join(browser_slots.folder(), f_))
        ask(cmd(), True)                                 # a new plain one: its job 1
        pid0 = next(r["pid"] for _, r in browser_slots.kept() if not r.get("variant"))
        ask(cmd(), True)
        ask(cmd(), True)                                 # job 3: retired after it
        ask(cmd(), True)                                 # a fresh kept Chrome's job 1
        pids = [r["pid"] for _, r in browser_slots.kept() if not r.get("variant")]
        t = time.time()
        while browser_slots.alive(pid0) and time.time() - t < 10:   # its keeper ends it within a second or two
            time.sleep(0.2)
        check("CF_CHROME_JOBS=3: after its third job the Chrome is restarted (a new one for the next job)",
              pids and pids[0] != pid0 and not browser_slots.alive(pid0), (pid0, pids))
        rec = next(r for _, r in browser_slots.kept() if not r.get("variant"))
        if os.name == "nt":                              # the keeper ended ALONE (not its tree): its Chrome must not outlive it
            subprocess.run(["taskkill", "/F", "/PID", str(rec["keeper"])], capture_output=True)
            t = time.time()
            while browser_slots.alive(int(rec["pid"])) and time.time() - t < 10:
                time.sleep(0.2)
            check("a keeper ended alone takes its Chrome with it (a job object) - no Chrome left running with no record",
                  not browser_slots.alive(int(rec["pid"])), rec)
        stall = os.path.join(tmp, "stall.html")
        io_write(stall, "<html><body><script>while (true) {}</script></body></html>")
        os.environ["CF_CHROME_REUSE"] = "on"
        c = cmd()
        c[-1] = Path(stall).as_uri()
        t = time.time()
        try:
            browser_slots.run_dom(c, timeout=5, capture_output=True, text=True)
            stalled = False
        except subprocess.TimeoutExpired:
            stalled = True
        check("a page that never settles ends in its time limit (TimeoutExpired, %.1f s) and its Chrome is not reused"
              % (time.time() - t), stalled and time.time() - t < 15 and not [1 for _, r in browser_slots.kept() if not r.get("variant")],
              browser_slots.kept())
        t = time.time()
        while browser_slots.kept() and time.time() - t < 90:
            time.sleep(0.5)
        check("CF_CHROME_IDLE=30: unused, every kept Chrome ends by itself and its record goes (%.0f s)" % (time.time() - t),
              not browser_slots.kept(),
              browser_slots.kept())
    finally:
        for k in ("CF_CHROME_JOBS", "CF_CHROME_IDLE", "CF_CHROME_REUSE"):
            os.environ.pop(k, None)
        for _, r in browser_slots.kept():
            browser_slots.kill_tree(int((r or {}).get("pid") or 0))
        shutil.rmtree(tmp, ignore_errors=True)


def io_write(path, text):
    with open(path, "w", encoding="ascii") as f:
        f.write(text)


def path_uri(p):
    from pathlib import Path
    return Path(p).as_uri()


if __name__ == "__main__":
    sys.exit(main())
