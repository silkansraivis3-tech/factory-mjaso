#!/usr/bin/env python3
"""test_scene3d_check.py - the workflow's 3D step, its script half (2.71.0): a module's 3D-kit scenes found from the build
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


def run(*a, env=None):
    p = subprocess.run([sys.executable, "-I", SCRIPT] + list(a), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, env=dict(os.environ, **(env or {})))
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
    # how a smoke3d.py and a perf3d.mjs answer is read, scene by scene - no browser needed
    sys.path.insert(0, HERE)
    import scene3d_check as sc
    said = ("  s05: first frame 420 ms\n    full screen 1280x800 px, drawing (12 frames); label none to tap\n"
            "FAIL 3D smoke test (61 s):\n  - s09: no first frame within 15 s\n  - s05: the Full screen button is 30x30 px - a tap needs 44\n")
    check("smoke: a scene's own problem line is its line, and it failed", sc.smoke_said(said, "s05") == (
        "- s05: the Full screen button is 30x30 px - a tap needs 44", True), sc.smoke_said(said, "s05"))
    check("smoke: a scene that never drew failed", sc.smoke_said(said, "s09")[1], sc.smoke_said(said, "s09"))
    check("smoke: a scene with only its first-frame line passed", sc.smoke_said("  s07: first frame 300 ms\n", "s07") ==
          ("s07: first frame 300 ms", False))
    check("smoke: a scene the run never named failed", sc.smoke_said("FAIL 3D smoke test (135 s): timed out", "s07")[1])
    check("perf: perf3d.mjs's \"OVER\" is a scene over the budget", sc.perf_over("s05          1840.2     -       -  OVER"))
    check("perf: \"OK\" is not", not sc.perf_over("s05           640.0     -       -  OK"))
    gate = ("slide          3D      ctx   first     med     p95  hidden    heap\ns27            kit3d     1      95    16.7    49.9       0"
            "    10.2\n1280x800  35 slides, 19 with 3D\n  s27  p95 frame 49.9 ms - 3.0 frames of 16.7 ms (at most 2: 33 ms)\n"
            "  s01  12 frames drawn by canvases not on the slide shown (at most 10)\nperf_gate: FAIL 2 slide(s), 2 finding(s)\n")
    check("perf_gate: each slide it names over its budget, with what (the trial's M01 passed its build with s27 lagging: no "
          "step ran perf_gate)", sc.lag_said(gate) == {"s27": ["p95 frame 49.9 ms - 3.0 frames of 16.7 ms (at most 2: 33 ms)"],
                                                        "s01": ["12 frames drawn by canvases not on the slide shown (at most 10)"]},
          sc.lag_said(gate))
    walks, real_run = [], sc.run
    second = "  s26  p95 frame 49.9 ms - 3.0 frames of 16.6 ms (at most 2: 33 ms)\n  s01  12 frames drawn by canvases not on the slide shown (at most 10)\n"
    try:
        sc.run = lambda cmd, timeout=600: walks.append(cmd) or ((1, gate) if len(walks) == 1 else (1, second))
        over = sc.lagging("deck.html")
        check("a slide over in one walk and not in the next is a busy computer, not lag; one over in both lags",
              len(walks) == 2 and over == {"s01": ["12 frames drawn by canvases not on the slide shown (at most 10)"]}, over)
        walks.clear()
        sc.run = lambda cmd, timeout=600: walks.append(cmd) or (0, "perf_gate: PASS - the 3D keeps up")
        check("... a deck within the budget is walked once", sc.lagging("deck.html") == {} and len(walks) == 1, walks)
        sc.run = lambda cmd, timeout=600: (2, "perf_gate: Playwright is not installed")
        check("... and one that could not be measured is no lag", sc.lagging("deck.html") == {})
        # the frames a second perf3d.mjs printed were judged by nothing: M19 s02 passed at 2.9 (the factory trial)
        res = {"s01": {"perf": "s01                          811.6       376    13.0  OK"},
               "s02": {"perf": "s02                             72     292.5     2.9  OK"},
               "s03": {"perf": "s03                           65.4     232.3     6.1  OK"}}
        walks.clear()
        sc.run = lambda cmd, timeout=600: walks.append(cmd) or (0, "s02    70    -    3.1  OK\ns03    60    -    12.4  OK\n")
        slow = sc.slow_turns("deck.html", res)
        check("perf3d: a scene under %d frames a second twice is slow (2.9, then 3.1); one fast the second time is not; one at 13 "
              "is not timed again" % sc.SOFT_FPS, slow == {"s02": 2.9} and len(walks) == 1 and "--slides=s02,s03" in walks[0], (slow, walks))
        check("perf3d: its line's frames a second are read", sc.perf_fps(res["s02"]["perf"]) == 2.9 and sc.perf_fps("no line") is None)
    finally:
        sc.run = real_run
    if not shutil.which("node"):
        print("SKIP - no Node")
        return 0
    tmp = tempfile.mkdtemp(prefix="test_scene3d_")
    try:
        c0 = course(os.path.join(tmp, "flat"), {"s03": {"figure": "s03.kit.json"}}, {})
        # the 2.126.0 trial: helpers sent a 3D check longer than the shell's 10 minutes to the background, ended their turns,
        # and claude -p quit with both checks unreported
        code, out = run(c0, "--module", "2", "--wait")
        check("--wait with no check to wait for says so", code == 1 and "No 3D check of M02 to wait for" in out, (code, out))
        code, out = run(c0, "--module", "2")
        check("a module with no 3D-kit scene: nothing to check (exit 2), said in one line", code == 2 and "No 3D-kit scene" in out, (code, out))
        slow = {"CF_3D_ANSWER_WITHIN": "1", "CF_3D_TEST_SLEEP": "4"}
        code, out = run(c0, "--module", "2", env=slow)
        check("a check longer than its answer time says STILL CHECKING (exit 3) and goes on by itself",
              code == 3 and "STILL CHECKING M02" in out and "--wait" in out and "never end your turn" in out, (code, out))
        code, out = run(c0, "--module", "2", env={"CF_3D_ANSWER_WITHIN": "1"})
        check("... the same command meanwhile waits for it, never a second check", "already running" in out, (code, out))
        code, out = run(c0, "--module", "2", "--wait", env={"CF_3D_ANSWER_WITHIN": "30"})
        check("... and --wait prints its answer and its exit", code == 2 and "No 3D-kit scene" in out, (code, out))
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
        two = course(os.path.join(tmp, "two"), {"s09": {"figure": "s09.kit3d.json"}, "s10": {"figure": "s10.kit3d.json"}},
                     {"s09.kit3d.json": tank, "s10.kit3d.json": tank})
        run(two, "--module", "2", "--no-perf", "--json")
        whole = sorted(os.listdir(os.path.join(two, "working_claude", "review", "M02_3d")))
        code, out = run(two, "--module", "2", "--slides", "s10", "--no-perf", "--json")
        try:
            r = json.loads(out[out.index("{"):])
        except ValueError:
            r = {}
        look = [x for sc_ in r.get("scenes") or [] for x in sc_.get("shots") or []]
        check("--slides: a look at only the scenes named, in its own folder - the reviewer's pictures of the whole module stay",
              [x.get("slide") for x in r.get("scenes") or []] == ["s10"] and look
              and all(os.sep + "M02_3d_look" + os.sep in os.path.normpath(p) for p in look)
              and sorted(os.listdir(os.path.join(two, "working_claude", "review", "M02_3d"))) == whole and whole, (out[-600:], whole))
        code, out = run(two, "--module", "2", "--slides", "s04", "--no-perf")
        check("... a slide with no scene: nothing to check, said with the slide", code == 2 and "on s04" in out, out)
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
