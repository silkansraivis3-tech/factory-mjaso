#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The picture Gemini downloaded is found, checked and moved to its slide's file, with its record.

    python test_gemini_take.py
"""
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "gemini_take.py")
PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + ("" if ok else "  -> %s" % str(detail)[:600]))


def run(*a):
    p = subprocess.run([sys.executable, TOOL] + list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


def png(w, h):
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\xff\xff" * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def main():
    tmp = tempfile.mkdtemp(prefix="gt_")
    try:
        dl, dest_dir = os.path.join(tmp, "Downloads"), os.path.join(tmp, "module01", "assets", "img")
        os.makedirs(dl)
        old = os.path.join(dl, "holiday.png")
        io.open(old, "wb").write(png(8, 8))
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        code, out = run("now")
        stamp = out.strip()
        check("now prints a stamp", code == 0 and stamp.isdigit(), out)
        dest = os.path.join(dest_dir, "m01_s04_bunkering_station_night.jpg")
        code, out = run("take", dest, "--since", stamp, "--downloads", dl)
        check("an older file in Downloads is never taken - exit 1, wait and run again", code == 1 and os.path.isfile(old), out)

        io.open(os.path.join(dl, "Gemini_Generated_Image_x.png.crdownload"), "wb").write(b"half")
        check("a download still running is not taken", run("take", dest, "--since", stamp, "--downloads", dl)[0] == 1)
        io.open(os.path.join(dl, "Gemini_Generated_Image_abc.png"), "wb").write(png(64, 36))
        code, out = run("take", dest, "--since", stamp, "--downloads", dl, "--about", "The bunkering station at night",
                        "--prompt", "A realistic documentary photograph of ...")
        r = json.loads(out.strip().splitlines()[-1]) if code == 0 else {}
        check("the new picture is moved to the slide's file; the extension follows the real format",
              code == 0 and r.get("file", "").endswith("m01_s04_bunkering_station_night.png") and os.path.isfile(r["file"])
              and not os.path.exists(os.path.join(dl, "Gemini_Generated_Image_abc.png")), out)
        check("its size is read from the file itself", r.get("width") == 64 and r.get("height") == 36, r)
        meta = json.load(io.open(os.path.join(dest_dir, "_photo_meta.json"), encoding="utf-8"))
        m = meta.get("m01_s04_bunkering_station_night.png", {})
        check("its record says generated, what it shows and the prompt - and that nobody has looked yet",
              m.get("generated") is True and m.get("description") == "The bunkering station at night"
              and m.get("generation_prompt", "").startswith("A realistic") and m.get("visually_verified", "").startswith("no"), m)

        io.open(os.path.join(dl, "page.png"), "wb").write(b"<html>not a picture</html>")
        check("a file that only has a picture's name is refused", run("take", dest, "--since", stamp, "--downloads", dl)[0] == 2)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
