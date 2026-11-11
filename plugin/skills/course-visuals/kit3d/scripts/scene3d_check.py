#!/usr/bin/env python3
"""scene3d_check.py - a module's 3D-kit scenes checked and photographed for a reviewer who did not build them (2.71.0).

  scene3d_check.py <course> --module 2 [--out <folder>] [--size 720x450] [--no-perf]

WHY (the 3D kit, 2.64.0 - "the 3D is shit compared to the handmade"): a builder judged its own scene, and the 2.63.2
whole-course run's scenes passed every check while showing "a bare pipe" and "labels as buttons below". The workflow's
3D step runs this, then gives the pictures to a SEPARATE reviewer (build_course.js, review3d) - 3D never relies on the
builder's own judgement. One command, in this order, each part judged as the build judges it:

  1 SPEC     check_kit3d.py spec on every *.kit3d.json the module's build sheet names (with assets/kit3d_parts.js), and
             on the built deck each scene's step lines against its slide's lines (counted from 1, up to the last)
  2 SMOKE    smoke3d.py on the built deck's slides that show them - loads, draws, stays quiet
  3 PERF     perf3d.mjs at 4x CPU, the warm first frame against the 1,000 ms budget and the frames a second the scene
             draws while it turns (under SOFT_FPS twice is a problem), then perf_gate.py: the deck walked with Next at 4x
             CPU and every slide timed - a scene whose turn lags (a p95 over two frames at 60 Hz, or fewer frames drawn by
             the scene itself) in two walks, or a deck that keeps contexts or draws off screen, is a problem here, so a
             module whose 3D lags does not pass its 3D step (--no-perf skips both)
  4 SHOTS    shot3d.mjs: the scene at each of its steps (it opens on the first), in a box of the slide's size, PNG files in
             --out (default working_claude\\review\\MNN_3d\\) - what the reviewer looks at

Prints one block per scene and the PNG paths; with --json the same as data. Exit 0 every scene passed 1-3 (the pictures
are for the review), 1 a check failed, 2 nothing to check (no 3D-kit scene in the build sheet) or bad input.

Like build_module.py, the check runs as its own process and answers within 9 minutes, under the shell's 10-minute limit;
a check still going then says STILL CHECKING (exit 3) and goes on by itself: the same command with --wait waits for it
and prints its answer. Never send it to the background, never end a turn while it runs.
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
import time
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
ANSWER_WITHIN = 540     # s: a check still running then goes on by itself, as a build does


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


def smoke_said(text, sid):
    """(the line smoke3d.py said of one scene, failed?) - its own problem line ("- s05: no first frame ...") before its
    first-frame line; a scene the run said nothing of failed too"""
    mine = [x.strip() for x in text.splitlines() if re.search(r"\b%s\b" % re.escape(sid), x)]
    line = next((x for x in mine if "FAIL" in x or x.startswith("- ")), mine[0] if mine else "")
    return line, "FAIL" in line or line.startswith("- ") or not line


def perf_over(line):
    """perf3d.mjs's line of a scene says it failed or is over the budget (it prints "OVER")"""
    return bool(re.search(r"\b(FAIL|over)\b", line, re.I))


SOFT_FPS = 10       # frames a second a scene draws while it turns at 4x CPU in software graphics (perf3d's stand-in chip)


def perf_fps(line):
    """the frames a second perf3d.mjs's line of a scene says it drew while it turned ("s02  72  292.5  2.9  OK"), or None"""
    m = re.match(r"^\s*\S+\s+(?:[\d.]+|-)\s+(?:[\d.]+|-)\s+([\d.]+)\s+(?:OK|OVER)\b", line or "")
    return float(m.group(1)) if m else None


def slow_turns(deck, res):
    """{slide id: fps} - the scenes perf3d.mjs timed under SOFT_FPS, timed again: under it both times. perf3d printed the
    frames a second and nothing judged them - M19 s02 passed at 2.9 (the factory trial)"""
    slow = {sid: perf_fps(r.get("perf")) for sid, r in res.items()}
    slow = {sid: f for sid, f in slow.items() if f is not None and f < SOFT_FPS}
    if not slow:
        return {}
    _, text = run(["node", os.path.join(MEASURE, "perf3d.mjs"), deck, "--slides=" + ",".join(sorted(slow)), "--budget-ms=1000",
                   "--throttle=4", "--gate=warm", "--no-cold"], 600)
    again = {sid: perf_fps(next((x.strip() for x in text.splitlines() if re.search(r"\b%s\b" % re.escape(sid), x)), ""))
             for sid in slow}
    return {sid: min(f, again[sid]) for sid, f in slow.items() if again.get(sid) is not None and again[sid] < SOFT_FPS}


def lag_said(text):
    """{slide id: [what]} - the slides perf_gate.py names over its budget ("  s27  p95 frame 49.9 ms - ...")"""
    out = {}
    for x in text.splitlines():
        m = re.match(r"^  (\S+)  (\S.*)$", x)
        if m:
            out.setdefault(m.group(1), []).append(m.group(2).strip())
    return out


def lagging(deck):
    """{slide id: [what]} - the slides perf_gate.py finds over its budget in two walks of the deck: a slide over it in the
    first walk counts when the second walk finds it over again (a busy computer slows a few frames of one walk on a slide
    it picks by chance - the 2.126.0 trial's M01 deck walked twice on one computer: s22 over the first time, s26 alone
    the second). {} within the budget, or when it could not be measured (no Playwright or no browser)"""
    first = {}
    for k in range(2):
        code, text = run([PY, os.path.join(MEASURE, "perf_gate.py"), deck], 900)
        said = lag_said(text) if code == 1 else {}
        if code == 1 and not said:
            said = {"(deck)": [(text.strip().splitlines() or ["failed"])[-1]]}
        if k:
            return {sid: xs for sid, xs in said.items() if sid in first}
        if not said:
            return {}
        first = said
    return {}


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
    lag = []
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
    # 2 smoke, 3 perf - on the built deck's slides; and each scene's step lines against its slide's lines
    if os.path.isfile(deck):
        import check_kit3d
        for sid, x in check_kit3d.deck_line_problems(io.open(deck, encoding="utf-8").read()):
            if sid in res:
                res[sid]["problems"].append("lines: " + x)
        ids = ",".join(sid for sid, _ in specs)
        # smoke3d.py gives the scenes 15 s each in one browser, then each late one a browser of its own (15 + 30 s)
        code, text = run([PY, os.path.join(MEASURE, "smoke3d.py"), deck, "--slide", ids], 60 * len(specs) + 120)
        for sid in res:
            line, failed = smoke_said(text, sid)
            res[sid]["smoke"] = line
            if code != 0 and failed:
                res[sid]["problems"].append("smoke3d: " + (line or (text.strip().splitlines() or ["did not run"])[-1]))
        if perf and shutil.which("node"):
            code, text = run(["node", os.path.join(MEASURE, "perf3d.mjs"), deck, "--slides=" + ids, "--budget-ms=1000",
                              "--throttle=4", "--gate=warm"], 600)
            for sid in res:
                line = next((x.strip() for x in text.splitlines() if re.search(r"\b%s\b" % re.escape(sid), x)), "")
                res[sid]["perf"] = line
                if code == 1 and perf_over(line):
                    res[sid]["problems"].append("perf3d: " + line)
            for sid, f in slow_turns(deck, res).items():
                res[sid]["problems"].append("perf3d: the scene drew %.1f frames a second while it turned, twice (at least %d at 4x "
                                            "CPU in software graphics) - lighten it: fewer parts, fewer labels, no flow while it "
                                            "turns" % (f, SOFT_FPS))
        if perf:
            over = lagging(deck)
            for sid in res:
                res[sid]["problems"] += ["perf_gate: " + x for x in over.pop(sid, [])]
            lag = ["perf_gate %s: %s" % (sid, x) for sid, xs in over.items() for x in xs]
    else:
        for sid in res:
            res[sid]["problems"].append("the deck is not built yet (%s) - build_module.py first" % deck)
    # 4 the pictures
    for sid, pngs, err in shots(specs, parts, out, size):
        res[sid]["shots"] = pngs
        if err:
            res[sid]["problems"].append("shots: " + err)
    rows = [res[sid] for sid, _ in specs]
    return {"module": mid, "out": out, "scenes": rows, "lag": lag, "ok": not any(r["problems"] for r in rows) and not lag}


def report(r):
    lines = ["3D scenes of %s - %d (pictures in %s)" % (r["module"], len(r["scenes"]), r["out"])]
    for s in r["scenes"]:
        lines.append("  %s  %s  %s" % (s["slide"], os.path.basename(s["spec"]), "OK" if not s["problems"] else "PROBLEMS"))
        for k in ("smoke", "perf"):
            if s.get(k):
                lines.append("      %s: %s" % (k, s[k]))
        lines += ["      - " + p for p in s["problems"]]
        lines += ["      picture: " + p for p in s.get("shots") or []]
    lines += ["  the deck: " + x for x in r.get("lag") or []]
    lines.append("3D: every scene loads, draws and is in time - now the separate visual review" if r["ok"] else
                 "3D: problems above - fix them in the spec (or kit3d_parts.js), rebuild, run this again")
    return "\n".join(lines)


def running_files(course, module):
    """(its record, its answer) in working_claude\\review - where the check that said STILL CHECKING is found again"""
    mid = "M%02d" % int(module)
    return workspace.claude_path(course, "review", mid + "_3d_running.json"), workspace.claude_path(course, "review", mid + "_3d_answer.txt")


def entry(argv=None):
    """the check as its own process: its answer within ANSWER_WITHIN s, else STILL CHECKING (exit 3) while it goes on;
    --wait: wait (again) for it. A check of the module already running is waited for, never started twice"""
    argv = list(sys.argv[1:] if argv is None else argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "-h" in argv or "--help" in argv:
        return main(argv)
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    known, _ = ap.parse_known_args(argv)
    try:
        m = int(known.module)
        rec_path, ans_path = running_files(workspace.work_folder(known.course, create=False), m)
    except Exception:                                    # noqa: BLE001 - main says what is wrong with the course or module
        return main([a for a in argv if a != "--wait"])
    import browser_slots
    try:
        within = float(os.environ.get("CF_3D_ANSWER_WITHIN") or ANSWER_WITHIN)
    except ValueError:
        within = ANSWER_WITHIN
    try:
        rec = json.load(io.open(rec_path, encoding="utf-8"))
    except (OSError, ValueError):
        rec = {}
    running = rec.get("exit") is None and browser_slots.alive(int(rec.get("pid") or 0))
    wait = "--wait" in argv
    if wait and not rec:
        print("No 3D check of M%02d to wait for - run scene3d_check.py without --wait" % m)
        return 1
    if running and not wait:
        print("A 3D check of M%02d is already running (started %.0f s ago) - waiting for it instead of starting another."
              % (m, time.time() - rec.get("started", time.time())))
    elif not wait:
        os.makedirs(os.path.dirname(rec_path), exist_ok=True)
        io.open(rec_path, "w", encoding="utf-8").write(json.dumps({"started": time.time()}))
        fh = io.open(ans_path, "w", encoding="utf-8")
        flags = (subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000) if os.name == "nt" else 0    # its own group, no window
        p = subprocess.Popen([PY, os.path.abspath(__file__)] + [a for a in argv if a != "--wait"], stdout=fh,
                             stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONIOENCODING="utf-8", CF_3D_RUNNING=rec_path),
                             creationflags=flags, **({} if os.name == "nt" else {"start_new_session": True}))
        fh.close()
        try:                                             # its PID, keeping an "exit" a very short check has written already
            rec = json.load(io.open(rec_path, encoding="utf-8"))
        except (OSError, ValueError):
            rec = {"started": time.time()}
        rec["pid"] = p.pid
        io.open(rec_path, "w", encoding="utf-8").write(json.dumps(rec))
    t0 = time.time()
    while True:
        try:
            rec = json.load(io.open(rec_path, encoding="utf-8"))
        except (OSError, ValueError):                    # being written this instant
            rec = None
        if rec is not None and (rec.get("exit") is not None or not browser_slots.alive(int(rec.get("pid") or 0))):
            sys.stdout.write(io.open(ans_path, encoding="utf-8", errors="replace").read() if os.path.isfile(ans_path) else "")
            if rec.get("exit") is None:
                print("The 3D check of M%02d ended without its answer (stopped from outside?) - run it again" % m)
                return 1
            return int(rec["exit"])
        if time.time() - t0 >= within:
            print("STILL CHECKING M%02d - the 3D check goes on by itself. Run the same command with --wait: it waits up to %.0f s "
                  "more and prints its answer. Never send it to the background, never end your turn while it runs." % (m, within))
            return 3
        time.sleep(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("course")
    ap.add_argument("--module", required=True)
    ap.add_argument("--out")
    ap.add_argument("--size", default="720x450", help="the scene's box, WxH (a two-column slide's at 1280 x 800)")
    ap.add_argument("--no-perf", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--wait", action="store_true", help="wait for this module's check that said STILL CHECKING")
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
    if os.environ.get("CF_3D_RUNNING"):                  # the check itself, started by entry(): its exit goes in the record
        _rec = os.environ["CF_3D_RUNNING"]
        try:
            time.sleep(float(os.environ.get("CF_3D_TEST_SLEEP") or 0))      # test_scene3d_check.py: a check that takes long
            _code = main()
        except SystemExit as _e:
            _code = _e.code if isinstance(_e.code, int) else 1
        except BaseException:                            # noqa: BLE001 - said in the answer file, then the record
            import traceback
            traceback.print_exc()
            _code = 1
        sys.stdout.flush()
        try:
            _r = json.load(io.open(_rec, encoding="utf-8"))
        except (OSError, ValueError):
            _r = {}
        _r["exit"] = _code
        io.open(_rec, "w", encoding="utf-8").write(json.dumps(_r))
        sys.exit(_code)
    sys.exit(entry())
