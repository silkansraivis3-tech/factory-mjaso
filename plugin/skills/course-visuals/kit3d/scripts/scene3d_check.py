#!/usr/bin/env python3
"""scene3d_check.py - a module's 3D-kit scenes checked and photographed for a reviewer who did not build them (2.71.0).

  scene3d_check.py <course> --module 2 [--out <folder>] [--size 720x450] [--no-perf]

WHY (the 3D kit, 2.64.0 - "the 3D is shit compared to the handmade"): a builder judged its own scene, and the 2.63.2
whole-course run's scenes passed every check while showing "a bare pipe" and "labels as buttons below". The workflow's
3D step runs this, then gives the pictures to a SEPARATE reviewer (build_course.js, review3d) - 3D never relies on the
builder's own judgement. One command, in this order, each part judged as the build judges it:

  1 SPEC     check_kit3d.py spec on every *.kit3d.json the module's build sheet names (with assets/kit3d_parts.js)
  2 SMOKE    smoke3d.py on the built deck's slides that show them - loads, draws, stays quiet
  3 PERF     perf3d.mjs at 4x CPU, the warm first frame against the 1,000 ms budget (--no-perf skips it)
  4 SHOTS    shot3d.mjs: the scene at each of its steps (it opens on the first), in a box of the slide's size, PNG files in
             --out (default working_claude\\review\\MNN_3d\\) - what the reviewer looks at

Prints one block per scene and the PNG paths; with --json the same as data. Exit 0 every scene passed 1-3 (the pictures
are for the review), 1 a check failed, 2 nothing to check (no 3D-kit scene in the build sheet) or bad input.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
KIT3D = os.path.dirname(HERE)
SKILLS = os.path.dirname(os.path.dirname(KIT3D))
FACTORY = os.path.join(SKILLS, "course-factory", "scripts")
MEASURE = os.path.join(SKILLS, "course-module-ux", "measure", "scripts")
sys.path.insert(0, FACTORY)
import workspace  # noqa: E402

PY = sys.executable
SPEC = ".kit3d.json"


def scenes(course, module):
    """[(slide id, spec path)] - every 3D-kit scene the module's build sheet puts on a slide"""
    mid = "M%02d" % int(module)
    sheet = workspace.claude_path(course, "script", mid + ".build.json")
    try:
        build = json.load(io.open(sheet, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    figdir = workspace.claude_path(course, "figures", mid)
    out = []
    for sid, e in sorted((build.get("screens") or {}).items()):
        f = str((e or {}).get("figure") or "").replace("\\", "/")
        if f.lower().endswith(SPEC):
            out.append((sid, os.path.normpath(os.path.join(figdir, f))))
    return out


def run(cmd, timeout=600):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 1, "timed out after %d s" % timeout
    except OSError as err:
        return 2, str(err)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    """the factory's skills folder, plus /_spec/<name> (the spec's folder) and /_parts.js (the module's kit3d_parts.js)"""
    mounts = {}

    def translate_path(self, path):
        p = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        for pre, folder in self.mounts.items():
            if p.startswith(pre):
                return os.path.join(folder, p[len(pre):].lstrip("/"))
        return super().translate_path(path)

    def log_message(self, *a):
        pass


class _Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        pass


def shots(specs, parts, out, size):
    """[(slide id, [png ...], error)] - each scene at rest and after each step, from studio3d.html in a box of `size`"""
    if not shutil.which("node"):
        return [(sid, [], "Node.js is not on this computer") for sid, _ in specs]
    handler = type("H", (_Quiet,), {"mounts": {}})
    for i, (sid, sp) in enumerate(specs):
        handler.mounts["/_spec%d/" % i] = os.path.dirname(sp)
    if parts:
        handler.mounts["/_parts/"] = os.path.dirname(parts)
    srv = _Server(("127.0.0.1", 0), functools.partial(handler, directory=SKILLS))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % srv.server_address[1]
    plan, want = [], []
    try:
        for i, (sid, sp) in enumerate(specs):
            try:
                spec = json.load(io.open(sp, encoding="utf-8"))
            except (OSError, ValueError):
                want.append((sid, []))
                continue
            n = len(spec.get("steps") or [])
            url = base + "course-visuals/kit3d/studio3d.html?spec=%s&w=%d&h=%d%s" % (
                urllib.parse.quote("/_spec%d/%s" % (i, os.path.basename(sp))), size[0], size[1],
                "&parts=/_parts/" + os.path.basename(parts) if parts else "")
            pngs = []
            for k in range(max(1, n)):                  # the scene opens on its first step (kit3d goStep, 0-based)
                png = os.path.join(out, "%s_%s.png" % (sid, "step%d" % (k + 1) if n else "rest"))
                shot = {"out": png, "clip": "#box", "settle": 1400, "probe": "JSON.stringify(k3.info().warnings||[])"}
                if k == 0:
                    shot.update(url=url, wait="window.k3ready")
                else:
                    shot["do"] = "k3.step(%d)" % k
                plan.append(shot)
                pngs.append(png)
            want.append((sid, pngs))
        tmp = tempfile.mkdtemp(prefix="scene3d_")
        try:
            pf = os.path.join(tmp, "plan.json")
            io.open(pf, "w", encoding="utf-8").write(json.dumps(plan))
            code, text = run(["node", os.path.join(HERE, "shot3d.mjs"), pf, "--w=%d" % (size[0] + 40), "--h=%d" % (size[1] + 40)])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        srv.shutdown()
    bad = {}
    for line in text.splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("error") or r.get("errors"):
            bad[r.get("out")] = r.get("error") or "; ".join(r["errors"])[:200]
    out_ = []
    for sid, pngs in want:
        err = "; ".join("%s: %s" % (os.path.basename(p), bad[p]) for p in pngs if p in bad)
        if not pngs:
            err = "the spec could not be read"
        elif code not in (0, 1) and not err:
            err = text.strip().splitlines()[-1] if text.strip() else "shot3d did not run"
        out_.append((sid, [p for p in pngs if os.path.isfile(p)], err))
    return out_


def check(course, module, out=None, size=(720, 450), perf=True):
    """{"scenes": [...], "ok": bool} or None when the module has no 3D-kit scene"""
    specs = scenes(course, module)
    if not specs:
        return None
    mid = "M%02d" % int(module)
    mdir = os.path.join(course, workspace.MODULES, "module%02d" % int(module))
    parts = os.path.join(mdir, "assets", "kit3d_parts.js")
    parts = parts if os.path.isfile(parts) else None
    deck = os.path.join(mdir, "presentation", "index.html")
    out = out or workspace.claude_path(course, "review", mid + "_3d")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out, exist_ok=True)
    res = {sid: {"slide": sid, "spec": sp, "problems": []} for sid, sp in specs}
    # 1 the specs
    cmd = [PY, os.path.join(HERE, "check_kit3d.py"), "spec"] + [sp for _, sp in specs] + (["--parts", parts] if parts else [])
    code, text = run(cmd, 120)
    for sid, sp in specs:
        mine = [x.strip() for x in text.splitlines() if os.path.basename(sp) in x and re.search(r"\b(problem|not|unknown|missing|"
                                                                                                 r"no such|invalid|error)\b", x, re.I)]
        if code not in (0,) and mine:
            res[sid]["problems"] += ["spec: " + x for x in mine]
        elif code not in (0,) and len(specs) == 1:
            res[sid]["problems"] += ["spec: " + x.strip() for x in text.splitlines() if x.strip()][:6]
    # 2 smoke, 3 perf - on the built deck's slides
    if os.path.isfile(deck):
        ids = ",".join(sid for sid, _ in specs)
        code, text = run([PY, os.path.join(MEASURE, "smoke3d.py"), deck, "--slide", ids], 300)
        for sid in res:
            line = next((x.strip() for x in text.splitlines() if re.search(r"\b%s\b" % re.escape(sid), x)), "")
            res[sid]["smoke"] = line
            if code != 0 and ("FAIL" in line or not line):
                res[sid]["problems"].append("smoke3d: " + (line or (text.strip().splitlines() or ["did not run"])[-1]))
        if perf and shutil.which("node"):
            code, text = run(["node", os.path.join(MEASURE, "perf3d.mjs"), deck, "--slides=" + ids, "--budget-ms=1000",
                              "--throttle=4", "--gate=warm"], 600)
            for sid in res:
                line = next((x.strip() for x in text.splitlines() if re.search(r"\b%s\b" % re.escape(sid), x)), "")
                res[sid]["perf"] = line
                if code == 1 and re.search(r"\b(FAIL|over)\b", line):
                    res[sid]["problems"].append("perf3d: " + line)
    else:
        for sid in res:
            res[sid]["problems"].append("the deck is not built yet (%s) - build_module.py first" % deck)
    # 4 the pictures
    for sid, pngs, err in shots(specs, parts, out, size):
        res[sid]["shots"] = pngs
        if err:
            res[sid]["problems"].append("shots: " + err)
    rows = [res[sid] for sid, _ in specs]
    return {"module": mid, "out": out, "scenes": rows, "ok": not any(r["problems"] for r in rows)}


def report(r):
    lines = ["3D scenes of %s - %d (pictures in %s)" % (r["module"], len(r["scenes"]), r["out"])]
    for s in r["scenes"]:
        lines.append("  %s  %s  %s" % (s["slide"], os.path.basename(s["spec"]), "OK" if not s["problems"] else "PROBLEMS"))
        for k in ("smoke", "perf"):
            if s.get(k):
                lines.append("      %s: %s" % (k, s[k]))
        lines += ["      - " + p for p in s["problems"]]
        lines += ["      picture: " + p for p in s.get("shots") or []]
    lines.append("3D: every scene loads, draws and is in time - now the separate visual review" if r["ok"] else
                 "3D: problems above - fix them in the spec (or kit3d_parts.js), rebuild, run this again")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--out")
    ap.add_argument("--size", default="720x450", help="the scene's box, WxH (a two-column slide's at 1280 x 800)")
    ap.add_argument("--no-perf", action="store_true")
    ap.add_argument("--json", action="store_true")
    o = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    course = workspace.work_folder(o.course, create=False)
    size = tuple(int(v) for v in o.size.lower().split("x"))
    r = check(course, o.module, o.out, size, not o.no_perf)
    if r is None:
        print("No 3D-kit scene in M%02d's build sheet (no *.kit3d.json figure) - nothing to check" % int(o.module))
        return 2
    print(json.dumps(r, ensure_ascii=False, indent=1) if o.json else report(r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
