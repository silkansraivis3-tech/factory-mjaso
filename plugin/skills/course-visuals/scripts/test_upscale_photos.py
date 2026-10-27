# -*- coding: utf-8 -*-
"""test_upscale_photos - a module's small photographs made sharp on this computer, never one with words in it (2.68.0).

    python test_upscale_photos.py

The enlarger itself (Real-ESRGAN, ~45 MB) is not needed: a stand-in with its command line (-i -o -n -m) enlarges four
times with Lanczos, so what is chosen, what is kept, what is written and what the pre-check says are all tested anywhere.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))
UP = os.path.join(HERE, "upscale_photos.py")
PRE = os.path.join(SKILLS, "course-factory", "compile", "scripts", "precheck.py")
sys.path.insert(0, os.path.join(SKILLS, "course-factory", "compile", "scripts"))
sys.path.insert(0, HERE)
import test_compile_module as tc  # noqa: E402
from image_size import pixel_size  # noqa: E402

PASS, FAIL = [], []
STAND_IN = r'''import sys
from PIL import Image
a = sys.argv[1:]
i, o = a[a.index("-i") + 1], a[a.index("-o") + 1]
im = Image.open(i)
im.resize((im.size[0] * 4, im.size[1] * 4), Image.LANCZOS).save(o)
'''


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(("  ok    " if ok else "  FAIL  ") + name + (("  -> " + str(detail)[:700]) if detail and not ok else ""))


def run(*args, env=None):
    p = subprocess.run([sys.executable] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, **(env or {})))
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="upscale_")
    try:
        eng = os.path.join(tmp, "engine")
        os.makedirs(os.path.join(eng, "models"))
        io.open(os.path.join(eng, "standin.py"), "w").write(STAND_IN)
        exe = os.path.join(eng, "realesrgan-ncnn-vulkan.cmd")
        io.open(exe, "w").write('@"%s" "%s" %%*\n' % (sys.executable, os.path.join(eng, "standin.py")))
        env = {"NOVIKONTAS_UPSCALER": exe}
        os.makedirs(os.path.join(tmp, "a"))
        c, md = tc.new_course(os.path.join(tmp, "a"), tc.script(screens=tc.SCREENS))
        meta = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
        for name, (w, h), desc, extra in (("ship_small.png", (400, 300), "A gas carrier at sea.", {}),
                                          ("sds_page.png", (420, 600), "Page 1 of the propane SDS.", {}),
                                          ("pump_room.png", (500, 330), "The cargo pump room.", {"ai_enlarge": False}),
                                          ("deck_big.png", (1200, 800), "The cargo deck.", {})):
            io.open(os.path.join(md, "assets", "img", name), "wb").write(tc.png(w, h, (w % 200, 90, 150)))
            meta[name] = dict(tc.PHOTO_META["ship.jpg"], description=desc, url_or_origin="https://example.org/" + name, **extra)
        tc.cs.save(os.path.join(md, "assets", "img", "_photo_meta.json"), meta)

        code, out = run(UP, "--check", env={"NOVIKONTAS_UPSCALER": os.path.join(tmp, "none.exe")})
        check("not installed: it says how to install it, and changes nothing (exit 3)", code == 3 and "github.com/xinntao/Real-ESRGAN" in out, out)
        code, out = run(UP, c, "--modules", "1", "--list", env=env)
        check("--list: a small photograph of a scene would be enlarged", "ship_small.png" in out and "would be enlarged" in out.split("ship_small.png")[1].splitlines()[0], out)
        check("... a picture with words in it never - the enlarger would make them sharp and WRONG",
              "left as it is - it holds words or numbers" in out.split("sds_page.png")[1].splitlines()[0], out)
        check("... nor one whose record says \"ai_enlarge\": false", "ai_enlarge" in out.split("pump_room.png")[1].splitlines()[0], out)
        check("... nor one of 1000 px or more - the plain enlargement does well there", "1200 px already" in out.split("deck_big.png")[1].splitlines()[0], out)
        code, out = run(UP, c, "--modules", "1", env=env)
        keep = os.path.join(c, "working_claude", "photo_originals", "M01", "ship_small.png")
        rec = tc.cs.load(os.path.join(md, "assets", "img", "_photo_meta.json"))
        check("enlarged: the photograph four times larger in the module, its original kept as the compile keeps it (L62)",
              code == 0 and pixel_size(os.path.join(md, "assets", "img", "ship_small.png")) == (1600, 1200) and pixel_size(keep) == (400, 300), out)
        check("... its record says how - honest about a picture an enlarger rebuilt",
              rec["ship_small.png"].get("enlarged", "").startswith("Real-ESRGAN realesrgan-x4plus on this computer, from 400 x 300 to 1600 x 1200"),
              rec["ship_small.png"])
        check("... and the word-carrying page is untouched", pixel_size(os.path.join(md, "assets", "img", "sds_page.png")) == (420, 600)
              and "enlarged" not in rec["sds_page.png"])
        code, out = run(UP, c, "--modules", "1", env=env)
        check("run again: nothing is done twice", "0 enlarged" in out, out)
        tc.build_of(c, lambda b: b["screens"].update({"s01": {"figure": "assets/img/ship_small.png"}}))
        code, out = run(PRE, c, "--module", "1")
        check("the pre-check: an enlarged photograph is judged at the size it was found, said - never a stop",
              code == 0 and "made sharp by the local enlarger (Real-ESRGAN)" in out and "ship_small.png from 400x300" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 72 + "\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
