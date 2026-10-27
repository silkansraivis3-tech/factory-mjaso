#!/usr/bin/env python3
"""upscale_photos.py - a module's small photographs made sharp on THIS computer: Real-ESRGAN, nothing sent anywhere (2.68.0).

    upscale_photos.py <course> [--modules 1,3-5]      every module, or those; once per photograph - the result is kept
    upscale_photos.py <course> --list                 what it would do, and why it leaves a photograph alone
    upscale_photos.py --check                         is the enlarger installed here

WHY (owner, 2026-10-27: "how to upscale existing photos with the plugin, without other outside AI use"): the compile's own
enlargement (L62, Lanczos and a light sharpening) makes a 400 px photograph soft instead of blocky - it cannot make detail.
Real-ESRGAN (github.com/xinntao/Real-ESRGAN, BSD-3, realesrgan-ncnn-vulkan) rebuilds edges and texture from a learned model,
on this computer's graphics card: the gas course's 425 px compressor room came out with sharp pipework (about 40 s a
photograph on an Intel graphics chip). It runs here, OUTSIDE the build - a module's dozen small pictures would add minutes
to every build: run it once on a course (an old one in the background), or let the photo step of a new course run it.

IT INVENTS DETAIL. A ship, a pump room, a tank are made sharper and look right; letters and numbers it would make sharp
and WRONG - so a picture whose record or name says it holds words (a page, a sheet, a label, a sign, a gauge, a screen,
a table, a chart, a plan ...) keeps the plain enlargement, and so does one whose record says "ai_enlarge": false.
Each enlarged photograph's record says so: "enlarged": "Real-ESRGAN realesrgan-x4plus on this computer, from W x H".

Where the enlarger is: NOVIKONTAS_UPSCALER (its .exe), else %USERPROFILE%/.novikontas/tools/realesrgan/ - the Windows
build realesrgan-ncnn-vulkan-20220424-windows.zip, unpacked there. Not installed: nothing changes, and it says how.
Exit: 0 done / nothing to do, 1 something failed, 2 bad input, 3 the enlarger is not installed.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from image_size import PHOTO_MIN_LONG, found_size  # noqa: E402

MODEL = "realesrgan-x4plus"
TARGET_LONG = 2400            # the long side it is saved at: sharp full screen on a 1920 projector, light on a tablet
AI_BELOW = 1000               # only a photograph found smaller than this: where it shows (the gas course's 425 px ones, ~40 s);
                              # at 940-1400 px it took 73-172 s for a little over what the plain enlargement gives
RELEASE = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
# a picture that holds words or numbers: never invented ones
WORDY = re.compile(r"(?i)\b(page|pages|sheet|sds|msds|table|label|labels|sign|signs|placard|screen|display|panel|gauge|"
                   r"gauges|reading|readout|chart|graph|diagram|drawing|plan|matrix|document|form|certificate|text|card|"
                   r"notice|code|manual|list|checklist|poster|plate|nameplate|marking|markings|number|numbers|letters|"
                   r"words|scale|dial|meter)\b")
IMAGES = (".jpg", ".jpeg", ".png", ".webp")


def engine():
    """the enlarger's .exe and its models folder, or (None, why)"""
    exe = os.environ.get("NOVIKONTAS_UPSCALER") or os.path.join(os.path.expanduser("~"), ".novikontas", "tools", "realesrgan",
                                                                "realesrgan-ncnn-vulkan.exe")
    models = os.path.join(os.path.dirname(exe), "models")
    if not os.path.isfile(exe):
        return None, ("the enlarger is not installed here: unpack %s into %s (or set NOVIKONTAS_UPSCALER to its .exe)"
                      % (RELEASE, os.path.dirname(exe)))
    return (exe, models), ""


def modules(course, spec):
    import workspace
    course = workspace.work_folder(course, create=False)
    root = os.path.join(course, "modules")
    found = {}
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        m = re.fullmatch(r"module(\d+)", name)
        if m:
            found[int(m.group(1))] = os.path.join(root, name)
    if spec:
        want = set()
        for part in spec.split(","):
            a, _, b = part.strip().partition("-")
            want |= set(range(int(a), int(b or a) + 1))
        found = {k: v for k, v in found.items() if k in want}
    return found, course


def plan(course, mdir, m):
    """[(file, its path, the original to enlarge, (w, h) found at, why it is left alone or '')]"""
    img = os.path.join(mdir, "assets", "img")
    try:
        meta = json.load(io.open(os.path.join(img, "_photo_meta.json"), encoding="utf-8"))
    except (OSError, ValueError):
        meta = {}
    keep_dir = os.path.join(course, "working_claude", "photo_originals", "M%02d" % m)
    out = []
    for name in sorted(os.listdir(img)) if os.path.isdir(img) else []:
        p = os.path.join(img, name)
        if not name.lower().endswith(IMAGES) or not os.path.isfile(p):
            continue
        rec = meta.get(name) if isinstance(meta.get(name), dict) else {}
        keep = os.path.join(keep_dir, name)
        size = found_size(p, keep if os.path.isfile(keep) else None)
        if not size or max(size) >= PHOTO_MIN_LONG:
            continue
        said = " ".join([name.replace("_", " ").replace("-", " "), str(rec.get("description") or ""), " ".join(rec.get("shows") or [])])
        why = ""
        if max(size) >= AI_BELOW:
            why = "%d px already - the plain enlargement does well there, and the enlarger would take minutes" % max(size)
        elif str(rec.get("enlarged") or "").startswith("Real-ESRGAN"):
            why = "done already"
        elif rec.get("ai_enlarge") is False:
            why = "its record says \"ai_enlarge\": false"
        elif WORDY.search(said):
            why = "it holds words or numbers (\"%s\") - an enlarger would make them sharp and wrong" % WORDY.search(said).group(0)
        src = keep if os.path.isfile(keep) else p
        out.append((name, p, src, size, why))
    return out


def enlarge(eng, src, dst, size):
    """Real-ESRGAN x4 on src, saved at dst no longer than TARGET_LONG on its long side, in dst's own format"""
    from PIL import Image
    exe, models = eng
    tmp = tempfile.mkdtemp(prefix="upscale_")
    try:
        inp = os.path.join(tmp, "in.png")
        Image.open(src).convert("RGB").save(inp)
        outp = os.path.join(tmp, "out.png")
        r = subprocess.run([exe, "-i", inp, "-o", outp, "-n", MODEL, "-m", models], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900, cwd=os.path.dirname(exe))
        if r.returncode != 0 or not os.path.isfile(outp):
            raise RuntimeError((r.stderr or r.stdout or "no picture came out").strip().splitlines()[-1][:200])
        big = Image.open(outp).convert("RGB")
        k = min(1.0, TARGET_LONG / float(max(big.size)))
        if k < 1.0:
            big = big.resize((int(round(big.size[0] * k)), int(round(big.size[1] * k))), Image.LANCZOS)
        ext = os.path.splitext(dst)[1].lower()
        if ext == ".png":
            big.save(dst, "PNG", optimize=True)
        elif ext == ".webp":
            big.save(dst, "WEBP", quality=90)
        else:
            big.save(dst, "JPEG", quality=90, optimize=True, progressive=True)
        return big.size
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def mark(mdir, name, size, new):
    """the photograph's record says how it was enlarged - honest about a picture an enlarger rebuilt"""
    p = os.path.join(mdir, "assets", "img", "_photo_meta.json")
    try:
        meta = json.load(io.open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return
    rec = meta.get(name)
    if not isinstance(rec, dict):
        return
    rec["enlarged"] = "Real-ESRGAN %s on this computer, from %d x %d to %d x %d (%s)" % (MODEL, size[0], size[1], new[0], new[1],
                                                                                         time.strftime("%Y-%m-%d"))
    io.open(p, "w", encoding="utf-8", newline="").write(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course", nargs="?")
    ap.add_argument("--modules")
    ap.add_argument("--list", action="store_true", help="say what it would do, change nothing")
    ap.add_argument("--check", action="store_true", help="is the enlarger installed here")
    a = ap.parse_args(argv)
    eng, why = engine()
    if a.check:
        print("the enlarger is installed: %s" % eng[0] if eng else why)
        return 0 if eng else 3
    if not a.course:
        ap.print_usage()
        return 2
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "course-factory", "scripts"))
    mods, course = modules(a.course, a.modules)
    if not mods:
        print("Stopped - no module folder matches %s under %s" % (a.modules or "(all)", a.course))
        return 2
    if not eng and not a.list:
        print("Nothing changed - " + why)
        return 3
    done = left = failed = 0
    for m, mdir in sorted(mods.items()):
        for name, p, src, size, why_not in plan(course, mdir, m):
            if why_not:
                left += 1
                print("M%02d %-40s %4d x %-4d  left as it is - %s" % (m, name[:40], size[0], size[1], why_not))
                continue
            if a.list:
                print("M%02d %-40s %4d x %-4d  would be enlarged" % (m, name[:40], size[0], size[1]))
                continue
            keep_dir = os.path.join(course, "working_claude", "photo_originals", "M%02d" % m)
            os.makedirs(keep_dir, exist_ok=True)
            keep = os.path.join(keep_dir, name)
            if src == p:                                   # the original as found is kept once, as the compile keeps it (L62)
                shutil.copyfile(p, keep)
                src = keep
            t = time.time()
            try:
                new = enlarge(eng, src, p, size)
            except Exception as e:                         # noqa: BLE001 - one picture failing never stops the rest
                failed += 1
                print("M%02d %-40s %4d x %-4d  FAILED - %s (the plain enlargement stays)" % (m, name[:40], size[0], size[1], e))
                continue
            mark(mdir, name, size, new)
            done += 1
            print("M%02d %-40s %4d x %-4d  -> %d x %d  (%.0f s)" % (m, name[:40], size[0], size[1], new[0], new[1], time.time() - t))
    print("\n%d enlarged, %d left as they are, %d failed%s" % (done, left, failed, " (a list only: nothing changed)" if a.list else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
