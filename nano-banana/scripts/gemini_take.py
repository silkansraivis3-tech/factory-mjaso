#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Take the picture Gemini just downloaded and put it where it belongs - the free browser route.

    gemini_take.py now
    gemini_take.py take <destination> --since <stamp> [--about "<what it shows>"] [--prompt "<prompt>"] [--downloads <dir>]

WHY THIS EXISTS
The Gemini app (gemini.google.com, the person's own Google AI Pro account) makes Nano Banana pictures at no cost per
picture, so the factory drives it in a browser instead of paying for the API. The browser saves each picture into
Downloads under Gemini's own name (Gemini_Generated_Image_xxxx.png). This script finds that file, checks it really is a
picture, moves it to the slide's own file and writes its record, so the model does not hunt through folders.

  now    prints a stamp - run it just before clicking Download; pass it to take as --since
  take   the newest picture in Downloads made after --since: checks it is a PNG / JPEG / WEBP, moves it to
         <destination> (the extension follows the real format), and writes its record into _photo_meta.json beside
         it: generated, what it shows, the prompt, the date - the record the course compiler reads (L56)
  clip   the built-in browser pane saves no downloads (tested 2026-10-16): after a REAL click on Gemini's
         "Copy image", saves the clipboard picture as PNG at <destination> with the same record. Refuses the
         picture it took last time, so a missed copy never files the previous picture twice
    gemini_take.py clip <destination> --expect <WxH from GB.wait> [--about "..."] [--prompt "..."]
  put    a picture the person made in their own browser (pasted into the chat, or saved anywhere): copies it to
         <destination> with the same record - the "you click, Claude does the rest" route
    gemini_take.py put <picture> <destination> [--about "..."] [--prompt "..."]

Prints one JSON line: {"ok": true, "file": ..., "width": ..., "height": ..., "bytes": ...}. Exit 0, 1 when no new
picture is there yet (wait and run again), 2 on bad input.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import struct
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
PARTIAL = (".crdownload", ".part", ".tmp", ".download")


def downloads_dir():
    return os.path.join(os.path.expanduser("~"), "Downloads")


def sniff(path):
    """(format, width, height) from the file's own header - never trust the name"""
    with open(path, "rb") as f:
        head = f.read(64 * 1024)
    if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        w, h = struct.unpack(">II", head[16:24])
        return "png", w, h
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        chunk = head[12:16]
        if chunk == b"VP8X":
            w = 1 + int.from_bytes(head[24:27], "little")
            h = 1 + int.from_bytes(head[27:30], "little")
            return "webp", w, h
        if chunk == b"VP8 ":
            w, h = struct.unpack("<HH", head[26:30])
            return "webp", w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L":
            b = head[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            return "webp", w, h
        return "webp", 0, 0
    if head[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(head):
            if head[i] != 0xFF:
                i += 1
                continue
            marker = head[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", head[i + 5:i + 9])
                return "jpg", w, h
            i += 2 + struct.unpack(">H", head[i + 2:i + 4])[0]
        return "jpg", 0, 0
    return None, 0, 0


def newest_picture(folder, since):
    """the newest finished picture file in folder modified at or after since"""
    best = None
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        low = name.lower()
        if not os.path.isfile(p) or low.endswith(PARTIAL) or not low.endswith(IMAGE_EXT):
            continue
        t = os.path.getmtime(p)
        if t >= since - 1 and (best is None or t > best[0]):
            best = (t, p)
    return best[1] if best else None


def write_meta(dest, about, prompt):
    meta_path = os.path.join(os.path.dirname(dest), "_photo_meta.json")
    try:
        meta = json.load(io.open(meta_path, encoding="utf-8")) if os.path.isfile(meta_path) else {}
    except ValueError:
        meta = {}
    rec = meta.get(os.path.basename(dest)) or {}
    rec.update({"generated": True, "source": "GENERATED", "origin": "generated illustration",
                "generated_by": "Gemini app (browser), Nano Banana", "rights_state": "PROJECT_OWNED",
                "date": time.strftime("%Y-%m-%d")})
    if about:
        rec["description"] = about
    if prompt:
        rec["generation_prompt"] = prompt
    rec["visually_verified"] = rec.get("visually_verified") or "no - open the picture and check it before use"
    meta[os.path.basename(dest)] = rec
    with io.open(meta_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return meta_path


def clipboard_png(out):
    """the picture on the Windows clipboard, saved as PNG at out - (ok, why)"""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grabclipboard()
        if img is None or isinstance(img, list):
            return False, "no picture on the clipboard - click Gemini's Copy image with a real click (computer left_click), not a script click"
        img.save(out, "PNG")
        return True, ""
    except ImportError:
        pass
    ps = ("Add-Type -AssemblyName System.Windows.Forms, System.Drawing; $i = [System.Windows.Forms.Clipboard]::GetImage(); "
          "if ($i) { $i.Save('%s', [System.Drawing.Imaging.ImageFormat]::Png); 'ok' } else { 'none' }" % out.replace("'", "''"))
    import subprocess
    r = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps], capture_output=True, text=True)
    if "ok" not in r.stdout:
        return False, "no picture on the clipboard - click Gemini's Copy image with a real click (computer left_click), not a script click"
    return True, ""


def cmd_clip(a):
    """the browser pane saves no downloads, but Gemini's Copy image puts the picture on the clipboard"""
    import hashlib
    base, _ = os.path.splitext(os.path.abspath(a.destination))
    dest = base + ".png"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".clip.png"
    ok, why = clipboard_png(tmp)
    if not ok:
        print(json.dumps({"ok": False, "why": why}))
        return 1
    digest = hashlib.sha256(open(tmp, "rb").read()).hexdigest()
    seen = os.path.join(os.path.expanduser("~"), ".config", "nano-banana", "last_clip.txt")
    if os.path.isfile(seen) and io.open(seen, encoding="utf-8").read().strip() == digest:
        os.remove(tmp)
        print(json.dumps({"ok": False, "why": "the clipboard still holds the picture taken last time - click Copy image on the new one"}))
        return 1
    fmt, w, h = sniff(tmp)
    if a.expect and a.expect.lower() != "%dx%d" % (w, h):
        os.remove(tmp)
        print(json.dumps({"ok": False, "why": "the clipboard holds a %dx%d picture, Gemini showed %s - it is not the new "
                          "picture: hover the picture, click Copy image again" % (w, h, a.expect)}))
        return 1
    os.replace(tmp, dest)
    os.makedirs(os.path.dirname(seen), exist_ok=True)
    io.open(seen, "w", encoding="utf-8").write(digest)
    meta = write_meta(dest, (a.about or "").strip(), (a.prompt or "").strip())
    print(json.dumps({"ok": True, "file": dest, "from": "clipboard", "format": fmt, "width": w, "height": h,
                      "bytes": os.path.getsize(dest), "record": meta,
                      "next": "open the picture with Read and check it before it is used"}, ensure_ascii=False))
    return 0


def cmd_put(a):
    """a picture the person made in their own browser and handed over (pasted into the chat, or saved anywhere)"""
    src = os.path.abspath(a.source)
    fmt, w, h = sniff(src) if os.path.isfile(src) else (None, 0, 0)
    if not fmt:
        print(json.dumps({"ok": False, "why": "%s is not a PNG, JPEG or WEBP picture" % src}))
        return 2
    base, _ = os.path.splitext(os.path.abspath(a.destination))
    dest = base + "." + fmt
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    meta = write_meta(dest, (a.about or "").strip(), (a.prompt or "").strip())
    print(json.dumps({"ok": True, "file": dest, "from": src, "format": fmt, "width": w, "height": h,
                      "bytes": os.path.getsize(dest), "record": meta,
                      "next": "open the picture with Read and check it before it is used"}, ensure_ascii=False))
    return 0


def cmd_take(a):
    folder = a.downloads or downloads_dir()
    if not os.path.isdir(folder):
        print(json.dumps({"ok": False, "why": "no Downloads folder at %s - pass --downloads" % folder}))
        return 2
    src = newest_picture(folder, a.since)
    if not src:
        print(json.dumps({"ok": False, "why": "no new picture in %s since the stamp yet - wait a few seconds and run again" % folder}))
        return 1
    fmt, w, h = sniff(src)
    if not fmt:
        print(json.dumps({"ok": False, "why": "%s is not a PNG, JPEG or WEBP picture - not moved" % src}))
        return 2
    base, _ = os.path.splitext(os.path.abspath(a.destination))
    dest = base + "." + fmt
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    meta = write_meta(dest, (a.about or "").strip(), (a.prompt or "").strip())
    print(json.dumps({"ok": True, "file": dest, "from": os.path.basename(src), "format": fmt, "width": w, "height": h,
                      "bytes": os.path.getsize(dest), "record": meta,
                      "next": "open the picture with Read and check it before it is used"}, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("now")
    t = sub.add_parser("take")
    t.add_argument("destination")
    t.add_argument("--since", type=float, required=True)
    t.add_argument("--about", default="")
    t.add_argument("--prompt", default="")
    t.add_argument("--downloads", default="")
    c = sub.add_parser("clip")
    c.add_argument("destination")
    c.add_argument("--about", default="")
    c.add_argument("--prompt", default="")
    c.add_argument("--expect", default="", help="the size GB.wait() reported, e.g. 1024x572 - anything else is refused")
    p = sub.add_parser("put")
    p.add_argument("source")
    p.add_argument("destination")
    p.add_argument("--about", default="")
    p.add_argument("--prompt", default="")
    a = ap.parse_args(argv)
    if a.cmd == "now":
        print("%.0f" % time.time())
        return 0
    return {"clip": cmd_clip, "put": cmd_put}.get(a.cmd, cmd_take)(a)


if __name__ == "__main__":
    sys.exit(main())
