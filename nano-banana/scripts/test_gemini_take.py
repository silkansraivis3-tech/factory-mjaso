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


def picture(w, h):
    """a smooth picture with some grain, like a render - every edge differs from every other"""
    from PIL import Image
    import random
    rnd = random.Random(7)
    img = Image.new("RGB", (w, h))
    img.putdata([(x * 255 // w, y * 255 // h, (x + y + rnd.randint(0, 6)) * 255 // (w + h + 6))
                 for y in range(h) for x in range(w)])
    return img


def stitch_and_grid(tmp):
    from PIL import Image
    caps, dest_dir = os.path.join(tmp, "tool-results"), os.path.join(tmp, "module02", "assets", "img")
    os.makedirs(caps)
    since = "%.0f" % time.time()
    for w, h, boxes in ((1024, 572, [(0, 0, 512, 572), (512, 0, 1024, 572)]),
                        (1024, 765, [(0, 0, 512, 382), (512, 0, 1024, 382), (0, 382, 512, 765), (512, 382, 1024, 765)])):
        whole = picture(w, h)
        files = []
        for k, box in enumerate(reversed(boxes)):                         # shuffled: the last tile captured first
            f = os.path.join(caps, "mcp-Claude_Browser-blob-%d-%d.png" % (w * h, k))
            whole.crop(box).save(f)
            files.append(f)
        Image.new("RGB", (240, 135)).save(os.path.join(caps, "mcp-Claude_Browser-blob-small-%d.png" % h))
        dest = os.path.join(dest_dir, "m02_s03_%d.png" % h)
        code, out = run("stitch", dest, "--expect", "%dx%d" % (w, h), "--since", since, "--captures", caps,
                        "--aspect", "16:9" if h == 572 else "4:3", "--about", "The cargo manifold", "--prompt", "A realistic ...")
        ok = code == 0 and os.path.isfile(dest) and Image.open(dest).convert("RGB").tobytes() == whole.tobytes()
        check("%dx%d: tiles captured in shuffled order are stitched back into the picture, pixel for pixel" % (w, h), ok, out)
        for f in files:
            os.remove(f)
    m = json.load(io.open(os.path.join(dest_dir, "_photo_meta.json"), encoding="utf-8")).get("m02_s03_572.png", {})
    check("the stitched picture gets the same record as put", m.get("generated") is True
          and m.get("description") == "The cargo manifold" and m.get("visually_verified", "").startswith("no"), m)

    whole = picture(1024, 572)
    wrong = []
    for k, box in enumerate([(0, 0, 512, 560), (512, 0, 1024, 560)]):            # a zoom that was not 1:1
        f = os.path.join(tmp, "wrong_%d.png" % k)
        whole.crop(box).save(f)
        wrong.append(f)
    dest = os.path.join(tmp, "module03", "assets", "img", "m03_s01.png")
    code, out = run("stitch", dest, "--expect", "1024x572", "--tiles", *wrong)
    check("tiles of the wrong height are refused and nothing is written", code == 1 and not os.path.exists(os.path.dirname(dest)), out)
    code, out = run("stitch", dest, "--expect", "1024x572", "--since", since, "--captures", caps)
    check("no tiles since the stamp (only a small capture) - refused, nothing written",
          code == 1 and not os.path.exists(os.path.dirname(dest)), out)
    code, out = run("stitch", dest, "--expect", "1024x765", "--aspect", "16:9", "--tiles", *wrong)
    check("a picture of the wrong shape is refused before any tile is read", code == 1 and not os.path.exists(dest), out)

    colours = [(200, 30, 30), (30, 160, 30), (30, 30, 200), (200, 200, 30), (30, 200, 200), (200, 30, 200)]
    parts = []
    for k, (c, size) in enumerate(zip(colours, [(1024, 572), (1024, 765), (765, 1024), (800, 800), (1024, 572), (640, 480)])):
        f = os.path.join(tmp, "part_%d.png" % k)
        Image.new("RGB", size, c).save(f)
        parts.append(f)
    dest = os.path.join(dest_dir, "m02_s09.png")
    code, out = run("grid", dest, *parts, "--cols", "3", "--rows", "2", "--aspect", "16:9", "--about", "Six gas carriers")
    g = Image.open(dest).convert("RGB") if code == 0 else None
    runs = []
    if g:
        for line in ([g.getpixel((x, g.height // 4)) for x in range(g.width)], [g.getpixel((g.width // 6, y)) for y in range(g.height)]):
            n, prev, seq = 0, None, []
            for px in line:
                if px != prev and prev is not None:
                    seq.append((prev, n))
                    n = 0
                n, prev = n + 1, px
            seq.append((prev, n))
            runs.append([n for px, n in seq if px != (255, 255, 255)])
    check("a grid of six pictures of different shapes: even cells, each picture in its own cell, in order",
          g is not None and g.size == (1600, 900) and len(runs[0]) == 3 and len(set(runs[0])) == 1
          and len(runs[1]) == 2 and len(set(runs[1])) == 1
          and [g.getpixel((g.width * (2 * i + 1) // 6, g.height * (2 * j + 1) // 4)) for j in range(2) for i in range(3)] == colours,
          [out, runs])
    m = json.load(io.open(os.path.join(dest_dir, "_photo_meta.json"), encoding="utf-8")).get("m02_s09.png", {})
    check("the grid's record says it is a grid of generated pictures", m.get("generated") is True
          and m.get("description") == "Six gas carriers (grid of 6 generated pictures)", m)
    check("a grid with the wrong number of pictures is refused",
          run("grid", os.path.join(dest_dir, "x.png"), *parts[:5], "--cols", "3", "--rows", "2")[0] == 2)


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
        stitch_and_grid(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
