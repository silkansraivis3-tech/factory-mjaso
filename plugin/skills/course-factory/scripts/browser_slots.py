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
    CF_CHROME_REUSE        off: every --dump-dom run starts its own Chrome (2.71.0: one kept Chrome per slot - run_dom)
    CF_CHROME_JOBS         jobs a kept Chrome runs before it is restarted (50); CF_CHROME_IDLE s unused before it ends (60)

A slot is held for exactly one browser's life and never while waiting for another slot, so no process can wait on
itself; a thread that already holds one and asks again gets the same one (re-entrant).
"""
from __future__ import annotations

import contextlib
import json
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


# s a module's first build waits at most for another one's. 2.63.3: 300. 2.71.0: 2700 - a queue, not a short wait: in the
# 2.71.0 M01-M03 run (seed_from on, so no module spent its first 40 min drawing) all three first builds reached the lock
# within 2 minutes; after 5 minutes the other two went anyway and the three figure stages ran together for 29-34 min on two
# performance cores (studio probes 2.9-4.9 s each, ~1 s alone). A stale holder (its PID gone) is still reclaimed at once
COLD_WAIT = 2700


@contextlib.contextmanager
def cold_turn(wait_max=None, first=False):
    """2.63.3 - one module's FIRST build (no figure measured yet: every figure probed, every fix tried) at a time on this
    computer; another first build waits for it, at most wait_max s (CF_COLD_WAIT, default 2700 since 2.71.0), then goes anyway.
    WHY (the 2.63.2 full-course run): wave 1's three first builds overlapped on a laptop with two performance cores - M01's
    took 1,076 s, past the builder's 600 s shell limit (one blind wait); M02/M03's figures 186-260 s. Started one after the
    other they share nothing and each runs at the machine's full speed. Yields the seconds it waited.
    first=True (2.71.0, build_module.py --long-pole - the course's biggest module, build_order.py): never waits - it takes
    the turn when it is free, so the others wait for IT, and goes at once when another holds it (2.63.3 M01-M03: M02, the
    long pole, waited behind M01's first build)"""
    try:
        limit = 0.0 if first else float(os.environ.get("CF_COLD_WAIT") or (COLD_WAIT if wait_max is None else wait_max))
    except ValueError:
        limit = COLD_WAIT
    d = folder()
    path = os.path.join(d, "cold_build.lock")
    t0, mine = time.time(), False
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ("%d\n" % os.getpid()).encode("ascii"))
            os.close(fd)
            mine = True
            break
        except FileExistsError:
            if stale(path):
                _reclaim(d, path)
                continue
        except OSError:
            pass
        if time.time() - t0 >= limit:
            break
        time.sleep(min(1.0, max(0.05, limit / 50.0)))
    beat = _Beat(path) if mine else None
    if beat:
        beat.start()
    try:
        yield time.time() - t0
    finally:
        if beat:
            beat.stop.set()
            for _ in range(20):
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
    Windows: a timed-out hidden Chrome left its GPU, utility and page processes running for a minute or more (2.62.1).
    CREATE_NO_WINDOW: without it every taskkill flashed a console window on the operator's screen (2.72.1)"""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, timeout=30,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.killpg(os.getpgid(pid), 9)
    except (OSError, subprocess.SubprocessError):
        pass


def run_tree(cmd, timeout=None, input=None, capture_output=False, started=None, **kw):
    """subprocess.run with the same answer, except that on a timeout the whole process tree is ended before
    TimeoutExpired is raised. started(popen), when given, is told the process as it starts - so a caller can end its
    tree early (kill_tree) when its answer is no longer wanted (build_module.py, a round that will be built again)"""
    if capture_output:
        kw["stdout"], kw["stderr"] = subprocess.PIPE, subprocess.PIPE
    if os.name != "nt":
        kw.setdefault("start_new_session", True)
    with subprocess.Popen(cmd, stdin=subprocess.PIPE if input is not None else None, **kw) as p:
        if started:
            started(p)
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


# ------------------------------------------------------------------ 2.71.0: one Chrome per slot, reused over CDP
# WHY (the 2.63.2 whole-course run: studio 2,900, review sheets 3,406, drawing check 687 hidden-browser runs; the 2.63.3
# M02 build 316 studio probes): every --dump-dom run started a fresh Chrome with a fresh profile. Measured on an IGF M02
# probe page (1296 x 895, budget 20 s): a fresh Chrome 1.29-1.58 s, the same page in a kept Chrome 0.54-0.95 s, the same
# report (only the page clock "virt" differs). So each slot keeps ONE Chrome (a "keeper" process holds it and ends it
# after CF_CHROME_IDLE s unused, 60), each job opens its page in a NEW browser context (nothing shared between jobs: no
# cookies, storage, cache), and the Chrome is restarted every CF_CHROME_JOBS jobs (50). A launch flag that changes how a
# page lays out or draws (--hide-scrollbars, --disable-3d-apis) is the keeper's own: one keeper per slot and flag set.
# Any flag this does not know, any CDP error: the job runs the old way, a fresh Chrome. CF_CHROME_REUSE=off: always.
REUSE_JOBS = 50
REUSE_IDLE = 60
# 2.72.4 - an invisible page's renderer is "backgrounded" by Chrome: Windows Idle priority (the 2.72.3 IGF run: every kept
# Chrome's renderers at Idle, a figure probe 10-17 s real for ~1 s of page clock, ~1.2 s alone; on a laptop with two fast
# cores such work runs on the slow ones). Puppeteer passes these on every launch; review_sheets.mjs and shot3d.mjs did already
FOREGROUND = ("--disable-renderer-backgrounding", "--disable-background-timer-throttling", "--disable-backgrounding-occluded-windows")
FG = 1              # in a kept Chrome's record: started with FOREGROUND (one started before is retired, not used)
_HARMLESS = ("--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--no-default-browser-check",
             "--allow-file-access-from-files", "--dump-dom") + FOREGROUND
_VARIANT = ("--hide-scrollbars", "--disable-3d-apis")          # launch flags that change the page: the keeper's own


def reuse_on():
    return (os.environ.get("CF_CHROME_REUSE") or "on").strip().lower() not in ("off", "0", "no", "false")


def _env_int(name, default):
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def dom_job(cmd):
    """(exe, url, (w, h), budget ms or None, variant flags) of a hidden-browser --dump-dom command, or None when it is not
    one this can run in a kept Chrome exactly as given"""
    if len(cmd) < 3 or "--dump-dom" not in cmd or not str(cmd[-1]).lower().startswith(("file:", "http:", "https:")):
        return None
    win, budget, variant = None, None, []
    for a in cmd[1:-1]:
        a = str(a)
        if a.startswith("--window-size="):
            try:
                win = tuple(int(v) for v in a.split("=", 1)[1].split(","))
            except ValueError:
                return None
        elif a.startswith("--virtual-time-budget="):
            try:
                budget = int(a.split("=", 1)[1])
            except ValueError:
                return None
        elif a.startswith("--user-data-dir="):
            continue
        elif a in _VARIANT:
            variant.append(a)
        elif a not in _HARMLESS:
            return None
    if not win or len(win) != 2 or "--disable-gpu" not in cmd or "--headless=new" not in cmd:
        return None
    return str(cmd[0]), str(cmd[-1]), win, budget, tuple(sorted(variant))


class _WS(object):
    """the smallest websocket client CDP needs (RFC 6455: masked text frames out, unmasked frames in, ping answered)"""

    def __init__(self, url, timeout):
        import socket
        from urllib.parse import urlsplit
        u = urlsplit(url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=timeout)
        import base64
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        self.sock.sendall(("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (u.path, u.hostname, u.port, key)).encode("ascii"))
        self.buf = bytearray()
        while b"\r\n\r\n" not in self.buf:
            c = self.sock.recv(4096)
            if not c:
                raise OSError("the browser closed the connection")
            self.buf += c
        i = self.buf.index(b"\r\n\r\n")
        if b" 101 " not in bytes(self.buf[:i]).split(b"\r\n")[0]:
            raise OSError("no websocket: %r" % bytes(self.buf[:80]))
        del self.buf[:i + 4]

    def settimeout(self, t):
        self.sock.settimeout(max(0.05, t))

    def send(self, text, op=0x1):
        import struct
        data = text.encode("utf-8") if isinstance(text, str) else text
        n, hdr = len(data), bytearray([0x80 | op])
        if n < 126:
            hdr.append(0x80 | n)
        elif n < 65536:
            hdr.append(0x80 | 126)
            hdr += struct.pack(">H", n)
        else:
            hdr.append(0x80 | 127)
            hdr += struct.pack(">Q", n)
        mask = os.urandom(4)
        m = int.from_bytes((mask * (n // 4 + 1))[:n], "big") if n else 0
        body = (int.from_bytes(data, "big") ^ m).to_bytes(n, "big") if n else b""
        self.sock.sendall(bytes(hdr) + mask + body)

    def _read(self, n):
        while len(self.buf) < n:
            c = self.sock.recv(1 << 18)
            if not c:
                raise OSError("the browser closed the connection")
            self.buf += c
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def recv(self):
        import struct
        msg = bytearray()
        while True:
            b0, b1 = self._read(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b1 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 0x9:
                self.send(data, 0xA)
                continue
            if op == 0x8:
                raise OSError("the browser closed the connection")
            if op == 0xA:
                continue
            msg += data
            if b0 & 0x80:
                return msg.decode("utf-8", "replace")

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class _CDP(object):
    def __init__(self, ws_url, deadline):
        self.deadline = deadline
        self.ws = _WS(ws_url, max(1.0, deadline - time.time()))
        self.n, self.events = 0, []

    def _next(self):
        left = self.deadline - time.time()
        if left <= 0:
            raise _JobTimeout()
        self.ws.settimeout(left)
        import socket
        try:
            return json.loads(self.ws.recv())
        except socket.timeout:
            raise _JobTimeout()

    def call(self, method, params=None, session=None):
        self.n += 1
        msg = {"id": self.n, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))
        while True:
            m = self._next()
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError("%s: %s" % (method, m["error"].get("message")))
                return m.get("result") or {}
            self.events.append(m)

    def wait(self, method, session):
        while True:
            for i, m in enumerate(self.events):
                if m.get("method") == method and m.get("sessionId") == session:
                    return self.events.pop(i)
            self.events.append(self._next())


class _JobTimeout(Exception):
    pass


def _keeper_file(slot_path, variant):
    """the kept Chrome's record for this slot and flag set: cf_browser_slots\\chrome_slot_0[.hide-scrollbars].json"""
    tag = "".join("." + v.lstrip("-") for v in variant)
    return os.path.join(os.path.dirname(slot_path), "chrome_%s%s.json" % (os.path.basename(slot_path)[:-len(".lock")], tag))


def _read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write_json(p, rec):
    tmp = "%s.%d.tmp" % (p, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f)
    for _ in range(40):                                  # Windows: the keeper may be reading it this instant
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.025)
    os.replace(tmp, p)


def _retire(state_file):
    """end a kept Chrome: its record goes, and its keeper ends the Chrome when it sees that (or here, if the keeper is gone)"""
    rec = _read_json(state_file) or {}
    try:
        os.remove(state_file)
    except OSError:
        pass
    if rec.get("pid") and not alive(int(rec.get("keeper") or 0)):
        kill_tree(int(rec["pid"]))


def current(rec, exe):
    """a kept Chrome's record still to be used: the same browser, it and its keeper alive, under CF_CHROME_JOBS jobs, started
    with the FOREGROUND flags (2.72.4)"""
    return bool(rec) and rec.get("exe") == exe and alive(int(rec.get("pid") or 0)) and alive(int(rec.get("keeper") or 0)) \
        and int(rec.get("jobs") or 0) < _env_int("CF_CHROME_JOBS", REUSE_JOBS) and rec.get("fg") == FG


def keeper_args(exe, prof, variant):
    """the kept Chrome's command line"""
    return [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--mute-audio", "--no-default-browser-check",
            "--allow-file-access-from-files", "--remote-debugging-port=0", "--user-data-dir=" + prof] + list(FOREGROUND) \
        + list(variant) + ["about:blank"]


def _kept(slot_path, exe, variant):
    """the record of this slot's kept Chrome for these flags - started when there is none (the keeper writes it)"""
    p = _keeper_file(slot_path, variant)
    rec = _read_json(p)
    if current(rec, exe):
        return p, rec
    if rec or os.path.exists(p):
        _retire(p)
    flags = 0
    kw = {}
    if os.name == "nt":                                  # its own process group, no window: it outlives the tool that started it
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000 | 0x00000008     # CREATE_NO_WINDOW | DETACHED_PROCESS
    else:
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "--keep", p, exe] + list(variant),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags,
                     close_fds=True, **kw)
    t0 = time.time()
    while time.time() - t0 < 30:
        rec = _read_json(p)
        if rec and rec.get("ws"):
            return p, rec
        time.sleep(0.05)
    raise OSError("the kept Chrome did not start")


def _dom_in_kept(slot_path, job, timeout):
    """run one --dump-dom job in this slot's kept Chrome: a new browser context, the window, the virtual-time budget (or
    the load event when the command had none), the page's DOM as text"""
    exe, url, (w, h), budget, variant = job
    p, rec = _kept(slot_path, exe, variant)
    rec.update(busy=os.getpid(), used=time.time())
    _write_json(p, rec)
    deadline = time.time() + (timeout or 600)
    cdp = None
    try:
        cdp = _CDP(rec["ws"], deadline)
        ctx = cdp.call("Target.createBrowserContext", {"disposeOnDetach": True})["browserContextId"]
        tid = cdp.call("Target.createTarget", {"url": "about:blank", "browserContextId": ctx, "width": w, "height": h})["targetId"]
        sid = cdp.call("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]
        cdp.call("Page.enable", session=sid)
        if budget:
            cdp.call("Emulation.setVirtualTimePolicy", {"policy": "pause"}, sid)
        cdp.call("Page.navigate", {"url": url}, sid)
        if budget:
            cdp.call("Emulation.setVirtualTimePolicy", {"policy": "pauseIfNetworkFetchesPending", "budget": budget}, sid)
            cdp.wait("Emulation.virtualTimeBudgetExpired", sid)
        else:
            cdp.wait("Page.loadEventFired", sid)
        r = cdp.call("Runtime.evaluate", {"expression": "document.documentElement.outerHTML", "returnByValue": True}, sid)
        text = ((r.get("result") or {}).get("value")) or ""
        cdp.call("Target.closeTarget", {"targetId": tid})
        cdp.call("Target.disposeBrowserContext", {"browserContextId": ctx})
        rec = _read_json(p) or rec
        rec.update(busy=None, used=time.time(), jobs=int(rec.get("jobs") or 0) + 1)
        _write_json(p, rec)
        if rec["jobs"] >= _env_int("CF_CHROME_JOBS", REUSE_JOBS):
            _retire(p)                                   # restarted every N jobs: the next job starts a fresh one
        return text
    except BaseException:
        _retire(p)                                       # a page that stalled or a broken connection: never reused
        raise
    finally:
        if cdp:
            cdp.ws.close()


def run_dom(cmd, timeout=None, reuse=True, **kw):
    """2.71.0 - a hidden browser's `--dump-dom` command (with its own flags, window, budget and URL) answered by this slot's
    kept Chrome when it can be, exactly as a fresh one answers it; else (or CF_CHROME_REUSE=off) run as given (run_tree).
    Holds a slot (re-entrant: inside slot() it is the same one). -> subprocess.CompletedProcess with the DOM as stdout;
    a page that does not finish in `timeout` raises subprocess.TimeoutExpired, as run_tree does.
    reuse=False: a few long pages of their own flag set (run_audits.py - two decks of 6-30 s; measured: a keeper started
    for them cost more than it saved, 14.9 -> 19.6 s on IGF M02) - a fresh Chrome, unless one is kept already"""
    job = dom_job(cmd) if reuse_on() else None
    if job and not reuse:
        with slot() as sp:
            rec = _read_json(_keeper_file(sp, job[4]))
            if not (rec and alive(int(rec.get("pid") or 0))):
                job = None
    with slot() as sp:
        if job:
            try:
                text = _dom_in_kept(sp, job, timeout)
                if kw.get("text") or kw.get("encoding") or kw.get("universal_newlines"):
                    return subprocess.CompletedProcess(cmd, 0, text, "")
                return subprocess.CompletedProcess(cmd, 0, text.encode("utf-8"), b"")
            except _JobTimeout:
                raise subprocess.TimeoutExpired(cmd, timeout)
            except Exception:                            # noqa: BLE001 - the old way, a fresh Chrome
                pass
        return run_tree(cmd, timeout=timeout, **kw)


def _bind(p):
    """Windows: put the kept Chrome (and every process it starts) in a job that ends them all when the keeper ends, however
    it ends - a keeper killed alone left its Chrome running with no record (seen while this was built). Returns the job
    handle, which must stay open; None elsewhere or when it cannot be made"""
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.OpenProcess.restype = wintypes.HANDLE

        class LIMITS(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("r", "w", "o", "rb", "wb", "ob")]

        class EXT(ctypes.Structure):
            _fields_ = [("Basic", LIMITS), ("Io", IO), ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]
        job = k32.CreateJobObjectW(None, None)
        info = EXT()
        info.Basic.LimitFlags = 0x2000                   # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info))   # Extended limits
        h = k32.OpenProcess(0x0101, False, p.pid)        # PROCESS_SET_QUOTA | PROCESS_TERMINATE
        ok = k32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(h))
        k32.CloseHandle(wintypes.HANDLE(h))
        return job if ok else None
    except Exception:                                    # noqa: BLE001 - the idle and retire rules still end it
        return None


def _keep(state_file, exe, variant):
    """the keeper: start Chrome for one slot and flag set, write its record, end it when the record goes (retired), when
    the browser dies, or after CF_CHROME_IDLE s with no job"""
    import shutil
    # its own profile folder: a keeper retired a moment ago may still be ending its Chrome and removing its folder
    prof = "%s.%d.profile" % (state_file[:-len(".json")], os.getpid())
    import glob
    for old in glob.glob(state_file[:-len(".json")] + ".*.profile"):     # left by a keeper ended from outside (a tool's tree killed)
        try:
            pid = int(old.rsplit(".", 2)[-2])
        except ValueError:
            continue
        if not alive(pid):
            shutil.rmtree(old, ignore_errors=True)
    shutil.rmtree(prof, ignore_errors=True)
    os.makedirs(prof, exist_ok=True)
    args = keeper_args(exe, prof, variant)
    kw = {} if os.name == "nt" else {"start_new_session": True}
    p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    job = _bind(p)                                       # noqa: F841 - held for the keeper's life: its Chrome ends with it
    port_file, t0 = os.path.join(prof, "DevToolsActivePort"), time.time()
    ws = None
    while time.time() - t0 < 30 and p.poll() is None:
        try:
            with open(port_file, encoding="ascii") as f:
                lines = f.read().split()
            if len(lines) >= 2:
                ws = "ws://127.0.0.1:%s%s" % (lines[0], lines[1])
                break
        except OSError:
            pass
        time.sleep(0.05)
    if not ws:
        kill_tree(p.pid)
        return 1
    _write_json(state_file, {"pid": p.pid, "keeper": os.getpid(), "ws": ws, "exe": exe, "variant": list(variant),
                             "jobs": 0, "busy": None, "used": time.time(), "fg": FG})
    idle = _env_int("CF_CHROME_IDLE", REUSE_IDLE)
    try:
        while p.poll() is None:
            time.sleep(1)
            rec = _read_json(state_file)
            if rec is None and os.path.exists(state_file):
                continue                                 # being written this instant
            if not rec or rec.get("keeper") != os.getpid():
                break                                    # retired
            busy = int(rec.get("busy") or 0)
            if (not busy or not alive(busy)) and time.time() - float(rec.get("used") or 0) > idle:
                break
    finally:
        kill_tree(p.pid)
        rec = _read_json(state_file)
        if rec and rec.get("keeper") == os.getpid():
            try:
                os.remove(state_file)
            except OSError:
                pass
        shutil.rmtree(prof, ignore_errors=True)
    return 0


def kept():
    """[(record file, record)] of the kept Chromes now - for a message, and for the tests"""
    d = folder()
    return [(f, _read_json(os.path.join(d, f))) for f in sorted(os.listdir(d)) if f.startswith("chrome_") and f.endswith(".json")]


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--keep":
        sys.exit(_keep(sys.argv[2], sys.argv[3], tuple(sys.argv[4:])))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("%d slot(s) on this computer (CF_BROWSER_SLOTS), lock files in %s" % (count(), folder()))
    for f, pid in held():
        print("  %s  held by PID %d%s" % (f, pid, "" if alive(pid) else " (not running - reclaimed on the next take)"))
    for f, rec in kept():
        print("  %s  a kept Chrome (PID %s), %s job(s)%s" % (f, (rec or {}).get("pid"), (rec or {}).get("jobs"),
                                                          " - busy" if (rec or {}).get("busy") else ""))
