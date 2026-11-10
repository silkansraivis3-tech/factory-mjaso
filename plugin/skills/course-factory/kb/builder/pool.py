# -*- coding: utf-8 -*-
"""The worker processes: every page range, scanned page and Office file is one task, run on several cores.

Tasks are added while results come back (a PDF's sample first, then its page ranges, then its scanned pages). A task
that raises is one failed task. A worker that dies outright (a crash inside MuPDF) breaks the pool: a new one is made
and the unfinished tasks run again once; a task that breaks it twice is reported as failed. jobs = 1 runs every task
in this process, in order - no processes at all.
"""
from __future__ import annotations

import os
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool


def default_jobs():
    return max(1, min((os.cpu_count() or 2) - 1, 6))


def _quiet():
    # Tesseract writes its own notes ("Line cannot be recognized") straight to the error stream; a worker's is closed
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)
    except OSError:
        pass
    try:
        import pymupdf
        pymupdf.TOOLS.mupdf_display_errors(False)
        pymupdf.TOOLS.mupdf_display_warnings(False)
    except Exception:                                        # noqa: BLE001
        pass


class Pool(object):
    def __init__(self, jobs):
        self.jobs = max(1, int(jobs or 1))
        self.queue = deque()             # (tag, fn, args, tries) not yet handed to a worker
        self.running = {}                # future -> (tag, fn, args, tries)
        self.ex = None

    def submit(self, tag, fn, *args, **kw):
        """Queue a task; first=True puts it ahead of the others (scanned pages, the slowest work, start early)."""
        (self.queue.appendleft if kw.get("first") else self.queue.append)((tag, fn, args, 0))

    def _executor(self):
        if self.ex is None:
            self.ex = ProcessPoolExecutor(max_workers=self.jobs, initializer=_quiet)
        return self.ex

    def _feed(self):
        # keep a few tasks per worker queued, so a big queue does not pin every argument in memory at once
        while self.queue and len(self.running) < self.jobs * 2:
            tag, fn, args, tries = self.queue.popleft()
            self.running[self._executor().submit(fn, *args)] = (tag, fn, args, tries)

    def results(self, timeout=30.0):
        """Yield (tag, ok, result-or-error) as tasks finish, and (None, None, None) every `timeout` seconds with no
        result, so the caller can say how far it is. New tasks may be submitted while this runs."""
        if self.jobs == 1:
            while self.queue:
                tag, fn, args, _ = self.queue.popleft()
                try:
                    yield tag, True, fn(*args)
                except Exception as e:                       # noqa: BLE001 - one failed task, not a failed run
                    yield tag, False, "%s: %s" % (type(e).__name__, e)
            return
        while self.queue or self.running:
            self._feed()
            done, _ = wait(list(self.running), timeout=timeout, return_when=FIRST_COMPLETED)
            if not done:
                yield None, None, None
                continue
            broken = False
            for fut in done:
                tag, fn, args, tries = self.running.pop(fut)
                try:
                    yield tag, True, fut.result()
                except BrokenProcessPool:
                    broken = True
                    if tries >= 1:
                        yield tag, False, "the reader stopped working on this part (a crash inside the PDF library)"
                    else:
                        self.queue.appendleft((tag, fn, args, tries + 1))
                except Exception as e:                       # noqa: BLE001
                    yield tag, False, "%s: %s" % (type(e).__name__, e)
            if broken:
                for fut, (tag, fn, args, tries) in list(self.running.items()):
                    self.queue.appendleft((tag, fn, args, tries + 1))
                self.running.clear()
                try:
                    self.ex.shutdown(wait=False, cancel_futures=True)
                except Exception:                            # noqa: BLE001
                    pass
                self.ex = None

    def close(self):
        if self.ex is not None:
            self.ex.shutdown(wait=True)
            self.ex = None
