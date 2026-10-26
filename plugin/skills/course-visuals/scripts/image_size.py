#!/usr/bin/env python3
"""A picture's size in pixels from its own header - JPEG, PNG, WebP, GIF - with the standard library only.

    from image_size import pixel_size
    pixel_size("assets/img/ship.jpg")   ->  (1600, 1071)  or  None when it cannot be read

Why (2.65.0, owner 2026-10-26: "images upscaled, not this pixel stuff", and "catch it before the build"): the asset
check and the pre-build check both need a photograph's real size, and neither may depend on an image library a
colleague's computer may not have.
"""
from __future__ import annotations

import struct

PHOTO_MIN_LONG = 1600       # a photograph is found at this size or larger on its long side (asset-pipeline.json)
PHOTO_FLOOR = 800           # below this, enlarging cannot make it sharp: find a larger original


def found_size(shipped, kept):
    """the size the photograph was FOUND at: the kept original's while the shipped file is still its enlargement (L62:
    1600 px on the long side, or four times the original, the same shape); the shipped file's once someone has put a new
    picture in its place"""
    s = pixel_size(shipped)
    k = pixel_size(kept) if kept else None
    if s and k and max(k) < max(s) and (max(s) == PHOTO_MIN_LONG or max(s) == 4 * max(k)) \
            and abs(s[0] / float(s[1]) - k[0] / float(k[1])) < 0.02:
        return k
    return s


def pixel_size(path):
    try:
        with open(path, "rb") as f:
            head = f.read(64)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", head[6:10])
            if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                kind = head[12:16]
                if kind == b"VP8X":
                    w = 1 + int.from_bytes(head[24:27], "little")
                    h = 1 + int.from_bytes(head[27:30], "little")
                    return w, h
                if kind == b"VP8 ":
                    w, h = struct.unpack("<HH", head[26:30])
                    return w & 0x3FFF, h & 0x3FFF
                if kind == b"VP8L":
                    b = head[21:25]
                    w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                    h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                    return w, h
                return None
            if head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        return None
                    if marker[1] in (0xD8, 0x01) or 0xD0 <= marker[1] <= 0xD7:
                        continue
                    seg = f.read(2)
                    if len(seg) < 2:
                        return None
                    n = struct.unpack(">H", seg)[0]
                    if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        data = f.read(5)
                        h, w = struct.unpack(">HH", data[1:5])
                        return w, h
                    f.seek(n - 2, 1)
    except (OSError, struct.error, IndexError):
        return None
    return None
