# -*- coding: utf-8 -*-
"""browser_slots - ONE limit on hidden browsers for the whole computer, shared by every process (2.57.0).

    with browser_slots.slot():          # waits for a free slot, holds it while the browser runs
        subprocess.run([exe, "--headless=new", ...])
    browser_slots.run(cmd, **kw)        # the same, for one subprocess.run

WHY (2026-10-20): a test suite, a module rebuild and two test re-runs at once each started their own hidden Chrome or
Edge - 14+ browsers, the CPU at 99 %, and every one of them slower than if they had waited their turn. Every place that
starts a hidden browser (the drawing check, figure_fit and the studio, run_audits, measure_slides, review_sheets.mjs,
perf3d.mjs, the tests that drive Chrome) now takes a slot from this one pool first; two builds, or a build and the test
suite, queue instead of piling up.

HOW: a slot is a lock file %TEMP%\\cf_browser_slots\\slot_N.lock, made with exclusive create (taken or not, never both),
holding the holder's PID; it is removed when the browser is done. A holder that crashed leaves its file behind: a file
whose PID is no longer running is reclaimed, and so is one whose holder stopped touching it (every 20 s while held) for
5 minutes - a crashed holder whose PID Windows gave to another process. The same files and rules are kept by
course-module-ux/measure/scripts/browser_slots.mjs, so Python and Node share the pool.

    CF_BROWSER_SLOTS       how many hidden browsers at once on this computer (default: a quarter of the cores, 2-8)
    CF_BROWSER_SLOT_DIR    the folder of the lock files (default %TEMP%\\cf_browser_slots) - a test's private pool

A slot is held for exactly one browser's life and never while waiting for another slot, so no process can wait on
itself; a thread that already holds one and asks again gets the same one (re-entrant).
"""
from __future__ import annotations

import contextlib
import os
import random
import subprocess
import sys
import tempfile
import threading
import time

HEARTBEAT = 20          # s between touches of a held slot's file
STALE = 300             # s without a touch: the holder is gone (its PID may belong to another process now)
_local = threading.local()


def count():
    """how many slots: CF_BROWSER_SLOTS, else a quarter of the cores, at least 2, at most 8 (2.62.1 - was half).
    Measured on a 14-thread laptop (Core Ultra 7 265U, 2 performance cores), IGF M01's figure stage, the same work:
    1 slot 65 s; 2 slots 35-37 s; 3-7 slots 31-50 s - no gain past 2, but 7 browsers held the CPU at 100 % and made a
    second build several times slower"""
    try:
        want = int(os.environ.get("CF_BROWSER_SLOTS") or 0)
    except ValueError:
        want = 0
    return max(1, want or min(8, max(2, (os.cpu_count() or 2) // 4)))


def folder():
    d = os.environ.get("CF_BROWSER_SLOT_DIR") or os.path.join(tempfile.gettempdir(), "cf_browser_slots")
    os.makedirs(d, exist_ok=True)
    return d


def alive(pid):
    """is a process with this PID running? (os.kill(pid, 0) would END it on Windows - never used there)"""
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ctypes.get_last_error() == 5          # access denied: it exists; anything else: it does not
        try:
            code = wintypes.DWORD()
            return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def holder(path):
    try:
        with open(path, encoding="ascii", errors="replace") as f:
            return int((f.read().split() or ["0"])[0])
    except (OSError, ValueError):
        return 0


def stale(path):
    """a slot whose holder is gone: its PID is not running, or it was not touched for STALE seconds"""
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False                                     # already gone: free, not stale
    return age > STALE or (age > 2 and not alive(holder(path)))   # 2 s: a file just made may not have its PID yet


def _reclaim(d, path):
    """remove a stale slot file - under a short lock of its own, so a slot just taken by another process is never removed
    by one that judged its predecessor stale"""
    guard = os.path.join(d, "reclaim.lock")
    try:
        if time.time() - os.path.getmtime(guard) > 30:   # a reclaimer that crashed in these few lines
            os.remove(guard)
    except OSError:
        pass
    try:
        os.close(os.open(guard, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except OSError:
        return
    try:
        if stale(path):
            os.remove(path)
    except OSError:
        pass
    finally:
        try:
            os.remove(guard)
        except OSError:
            pass


def _take(d, n):
    """the path of a slot just taken, or None when every slot is held"""
    start = random.randrange(n)
    for k in range(n):
        path = os.path.join(d, "slot_%d.lock" % ((start + k) % n))
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if stale(path):
                _reclaim(d, path)
            continue
        except OSError:                                  # Windows: a file being removed this instant
            continue
        try:
            os.write(fd, ("%d\n" % os.getpid()).encode("ascii"))
        finally:
            os.close(fd)
        return path
    return None


class _Beat(threading.Thread):
    def __init__(self, path):
        threading.Thread.__init__(self, daemon=True)
        self.path, self.stop = path, threading.Event()

    def run(self):
        while not self.stop.wait(HEARTBEAT):
            try:
                os.utime(self.path)
            except OSError:
                pass


@contextlib.contextmanager
def slot(wait_note=None):
    """hold one slot of the computer's pool while the block runs (a hidden browser's life). wait_note(seconds) is called
    once when the wait is long (10 s), so a build can say it is queued behind other browsers"""
    if getattr(_local, "depth", 0):                     # this thread already holds one: the same slot
        _local.depth += 1
        try:
            yield _local.path
        finally:
            _local.depth -= 1
        return
    d, n = folder(), count()
    t0, said, pause = time.time(), False, 0.05
    path = _take(d, n)
    while path is None:
        time.sleep(pause + random.random() * pause)
        pause = min(0.5, pause * 1.5)
        if wait_note and not said and time.time() - t0 > 10:
            said = True
            wait_note(time.time() - t0)
        path = _take(d, n)
    beat = _Beat(path)
    beat.start()
    _local.depth, _local.path = 1, path
    try:
        yield path
    finally:
        _local.depth, _local.path = 0, None
        beat.stop.set()
        for _ in range(20):                             # Windows: the heartbeat may have it open this instant
            try:
                os.remove(path)
                break
            except FileNotFoundError:
                break
            except OSError:
                time.sleep(0.05)


def run(cmd, **kw):
    """subprocess.run(cmd, **kw) while holding a slot - a timeout ends the browser's whole process tree (run_tree)"""
    with slot():
        return run_tree(cmd, **kw)


def kill_tree(pid):
    """end a process and every process it started. subprocess's own kill ends only the browser's first process on
    Windows: a timed-out hidden Chrome left its GPU, utility and page processes running for a minute or more (2.62.1)"""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, timeout=30)
        else:
            os.killpg(os.getpgid(pid), 9)
    except (OSError, subprocess.SubprocessError):
        pass


def run_tree(cmd, timeout=None, input=None, capture_output=False, **kw):
    """subprocess.run with the same answer, except that on a timeout the whole process tree is ended before
    TimeoutExpired is raised"""
    if capture_output:
        kw["stdout"], kw["stderr"] = subprocess.PIPE, subprocess.PIPE
    if os.name != "nt":
        kw.setdefault("start_new_session", True)
    with subprocess.Popen(cmd, stdin=subprocess.PIPE if input is not None else None, **kw) as p:
        try:
            out, err = p.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(p.pid)
            p.kill()
            p.communicate()
            raise
        return subprocess.CompletedProcess(p.args, p.returncode, out, err)


def held():
    """[(slot file, PID)] of the slots held now - for a message, and for the tests"""
    d = folder()
    return [(f, holder(os.path.join(d, f))) for f in sorted(os.listdir(d)) if f.startswith("slot_") and f.endswith(".lock")]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("%d slot(s) on this computer (CF_BROWSER_SLOTS), lock files in %s" % (count(), folder()))
    for f, pid in held():
        print("  %s  held by PID %d%s" % (f, pid, "" if alive(pid) else " (not running - reclaimed on the next take)"))
