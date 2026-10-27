# -*- coding: utf-8 -*-
"""test_photo_focus - a photograph a frame crops keeps its subject: the compiler finds where it is (2.69.0).

    python test_photo_focus.py

Gas M01 s11 (owner's screenshot, 2026-10-27): a ship photo in a wide band showed the sky and a mast - the crop took the
middle. compile_module.photo_focus finds the part of the picture with the most detail (or reads the record's "focus") and
the photo's <img> gets object-position there.
"""
from __future__ import annotations

import os
import random
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compile_module as cm  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:500]) if detail and not ok else ""))


def scene(path, box, size=(1600, 830)):
    """a pale sky over a calm sea, and a 'ship' full of edges in box (fractions x0, y0, x1, y1)"""
    W, H = size
    im = Image.new("RGB", size, (200, 215, 230))
    d = ImageDraw.Draw(im)
    d.rectangle([0, int(H * .62), W, H], fill=(70, 90, 110))
    rnd = random.Random(7)
    for _ in range(400):                                   # ripples on the sea: weak edges
        x, y = rnd.randrange(W), rnd.randrange(int(H * .62), H)
        d.line([x, y, x + 30, y], fill=(78, 98, 118))
    x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
    for i in range(x0, x1, 14):                            # the ship: strong edges, stripes of white and red on dark blue
        d.rectangle([i, y0, i + 7, y1], fill=(255, 255, 255) if (i // 14) % 2 else (200, 40, 30))
    d.rectangle([x0, int(y0 + (y1 - y0) * .6), x1, y1], fill=(20, 40, 90))
    im.save(path)


def main():
    tmp = tempfile.mkdtemp(prefix="focus_")
    try:
        img = os.path.join(tmp, "assets", "img")
        os.makedirs(img)
        scene(os.path.join(img, "ship.jpg"), (0.10, 0.45, 0.55, 0.78))
        f = cm.photo_focus(tmp, "assets/img/ship.jpg", {})
        check("a ship low and left in the picture: the focus is low and left (x under 45 %, y 55 % or more)",
              f is not None and f[0] < 45 and f[1] >= 55, f)
        check("... rounded to 5 %", f is not None and f[0] % 5 == 0 and f[1] % 5 == 0, f)
        scene(os.path.join(img, "mid.jpg"), (0.35, 0.35, 0.65, 0.65))
        check("a subject in the middle: no focus written (the frame's own default)", cm.photo_focus(tmp, "assets/img/mid.jpg", {}) is None,
              cm.detail_centre(os.path.join(img, "mid.jpg")))
        check("the record's \"focus\": [x, y] wins over what is found",
              cm.photo_focus(tmp, "assets/img/ship.jpg", {"focus": [70, 30]}) == (70, 30))
        check("... and is kept inside 0-100", cm.photo_focus(tmp, "assets/img/ship.jpg", {"focus": [-5, 140]}) == (0, 100))
        attrs = cm.photo_panel({"description": "A gas carrier."}, "Credit", "assets/img/ship.jpg", [], "s01", tmp)
        check("the photo's <img> attributes carry object-position at the focus",
              'style="object-position:%d%% %d%%"' % f in attrs and 'data-about="A gas carrier."' in attrs, attrs)
        check("... none without the module folder (a caller that does not know it)",
              "style=" not in cm.photo_panel({"description": "x"}, "", "assets/img/ship.jpg", [], "s01"))
        check("a file that is not there: no focus, no error", cm.photo_focus(tmp, "assets/img/none.jpg", {}) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
