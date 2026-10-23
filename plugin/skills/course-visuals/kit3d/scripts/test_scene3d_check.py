#!/usr/bin/env python3
"""test_scene3d_check.py - the workflow's 3D step, its script half (2.65.0): a module's 3D-kit scenes found from the build
sheet, checked, and photographed at every step for a reviewer who did not build them. Needs Node and Chrome; ~1 minute.

    python test_scene3d_check.py
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
KIT3D = os.path.dirname(HERE)
SCRIPT = os.path.join(HERE, "scene3d_check.py")
FAILS = []


def check(what, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + what + ("" if ok else "  -> %s" % (detail,)))
    if not ok:
        FAILS.append(what)


def run(*a):
    p = subprocess.run([sys.executable, "-I", SCRIPT] + list(a), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def course(root, sheet, specs):
    os.makedirs(os.path.join(root, "working_claude", "script"), exist_ok=True)
    os.makedirs(os.path.join(root, "working_claude", "figures", "M02"), exist_ok=True)
    os.makedirs(os.path.join(root, "modules", "module02"), exist_ok=True)
    json.dump({"module": 2, "screens": sheet}, io.open(os.path.join(root, "working_claude", "script", "M02.build.json"), "w",
                                                        encoding="utf-8"))
    for name, src in specs.items():
        shutil.copyfile(src, os.path.join(root, "working_claude", "figures", "M02", name))
    return root


def main():
    if not shutil.which("node"):
        print("SKIP - no Node")
        return 0
    tmp = tempfile.mkdtemp(prefix="test_scene3d_")
    try:
        c0 = course(os.path.join(tmp, "flat"), {"s03": {"figure": "s03.kit.json"}}, {})
        code, out = run(c0, "--module", "2")
        check("a module with no 3D-kit scene: nothing to check (exit 2), said in one line", code == 2 and "No 3D-kit scene" in out, (code, out))
        tank = os.path.join(KIT3D, "examples", "m02_tank.kit3d.json")
        nsteps = len(json.load(io.open(tank, encoding="utf-8")).get("steps") or [])
        c = course(os.path.join(tmp, "c"), {"s09": {"figure": "s09.kit3d.json", "visual_kind": "model_3d"}, "s03": {"figure": "x.kit.json"}},
                   {"s09.kit3d.json": tank})
        code, out = run(c, "--module", "2", "--no-perf", "--json")
        try:
            r = json.loads(out[out.index("{"):])
        except ValueError:
            r = {}
        s = (r.get("scenes") or [{}])[0]
        check("the scene the build sheet names is found (and only it)", len(r.get("scenes") or []) == 1 and s.get("slide") == "s09", out[-800:])
        check("one picture per step of the scene (%d), each a real PNG of the scene's box" % nsteps,
              len(s.get("shots") or []) == max(1, nsteps) and all(os.path.getsize(p) > 5000 for p in s.get("shots") or []),
              s.get("shots"))
        check("a module not built yet is said, not passed (smoke3d needs the deck): exit 1",
              code == 1 and any("not built yet" in p for p in s.get("problems") or []) and r.get("ok") is False, (code, s.get("problems")))
        check("the pictures are not the same picture (the steps change what the scene shows)",
              len({io.open(p, "rb").read() for p in s.get("shots") or []}) == len(s.get("shots") or []), s.get("shots"))
        bad = json.load(io.open(tank, encoding="utf-8"))
        bad["parts"][0]["type"] = "no_such_part"
        io.open(os.path.join(c, "working_claude", "figures", "M02", "s09.kit3d.json"), "w", encoding="utf-8").write(json.dumps(bad))
        code, out = run(c, "--module", "2", "--no-perf")
        check("a spec check_kit3d.py refuses is a problem of its scene", code == 1 and "spec:" in out, out[-600:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n%s" % ("ALL PASS" if not FAILS else "%d FAILED" % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
