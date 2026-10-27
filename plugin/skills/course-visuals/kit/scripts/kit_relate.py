#!/usr/bin/env python3
"""kit_relate.py - a figure spec's relations resolved, and every part's box and ports, by kit.js itself (2.72.0)

  kit_relate.py <file.kit.json> ...         print each spec resolved (x / y / d filled in from "on", "at", "from"/"to" ...)
  kit_relate.py --geometry <file.kit.json>  print every part's box and ports in figure units

There is ONE resolver: the `/* kit-relate */` block of kit.js, the very code that places the parts on a slide. It is pure
(no DOM), so this runs it under node - check_kit.py judges what a figure MEANS on the geometry the deck draws, never on a
second copy of the rules that could drift (2.72.0). node is already needed by the build (the review sheets).
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT_JS = os.path.join(KIT, "kit.js")
BLOCK = re.compile(r"/\*\s*kit-relate\s*\*/(.*?)/\*\s*end kit-relate\s*\*/", re.S)

# node reads the block and a list of specs on stdin, and answers [{spec, geometry}, ...]
RUNNER = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[1], 'utf8');
const m = /\/\*\s*kit-relate\s*\*\/([\s\S]*?)\/\*\s*end kit-relate\s*\*\//.exec(src);
const RELATE = new Function(m[1] + '\nreturn RELATE;')();
let raw = '';
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  const out = JSON.parse(raw).map((s) => {
    try { const r = RELATE.resolve(s); return { spec: r, geometry: RELATE.geometry(r) }; }
    catch (e) { return { error: String(e && e.message || e) }; }
  });
  process.stdout.write(JSON.stringify(out));
});
"""

_CACHE = {}


def node():
    return shutil.which("node") or shutil.which("node.exe")


def available():
    return bool(node()) and os.path.isfile(KIT_JS) and bool(BLOCK.search(io.open(KIT_JS, encoding="utf-8").read()))


def run(specs, kit_js=KIT_JS):
    """[{spec, geometry}] for each spec (dicts), in one node run; None when node is not there"""
    exe = node()
    if not exe:
        return None
    keys = [json.dumps(s, sort_keys=True) for s in specs]
    todo = [i for i, k in enumerate(keys) if k not in _CACHE]
    if todo:
        p = subprocess.run([exe, "-e", RUNNER, kit_js], input=json.dumps([specs[i] for i in todo]).encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if p.returncode:
            raise RuntimeError("kit_relate: node failed - %s" % p.stderr.decode("utf-8", "replace")[-600:])
        for i, r in zip(todo, json.loads(p.stdout.decode("utf-8"))):
            _CACHE[keys[i]] = r
    return [_CACHE[k] for k in keys]


def resolve(spec):
    """the spec with its relations resolved (a copy); the spec itself when node is not there"""
    r = run([spec])
    return r[0].get("spec", spec) if r else spec


def has_relations(spec):
    for p in (spec or {}).get("parts") or []:
        if not isinstance(p, dict):
            continue
        if any(p.get(k) not in (None, "") for k in ("on", "in", "at", "for", "around", "aim")):
            return True
        if p.get("type") in ("pipe", "hose", "wire") and (p.get("from") or p.get("to")):
            return True
        if p.get("type") == "gas_cloud" and isinstance(p.get("from"), str):
            return True
    return False


def freeze(spec):
    """the spec with every relation written out as plain x / y / d (and the relation kept as "_on", "_from" ...) - for a
    tool that moves parts by their x (figure_fit.py): a moved part would otherwise snap back to what it stands on"""
    if not has_relations(spec):
        return spec
    out = resolve(spec)
    for p in out.get("parts") or []:
        if not isinstance(p, dict):
            continue
        for k in ("on", "in", "at", "for", "around", "aim", "side"):
            if k in p and not (k == "side" and not isinstance(p[k], str)):      # an airlock's "side" is a width
                p["_" + k] = p.pop(k)
        if p.get("type") in ("pipe", "hose", "wire"):                           # a boil_off's "level" is its own
            for k in ("from", "to", "via", "level", "route"):
                if k in p:
                    p["_" + k] = p.pop(k)
    out.pop("_relate", None)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    geo = "--geometry" in argv
    files = [a for a in argv if a != "--geometry"]
    if not files:
        print(__doc__)
        return 2
    if not node():
        print("kit_relate: node is not installed - it runs kit.js's resolver")
        return 2
    specs = [json.load(io.open(f, encoding="utf-8")) for f in files]
    for f, r in zip(files, run(specs)):
        print("== %s" % f)
        print(json.dumps(r.get("geometry") if geo else r.get("spec"), indent=1, ensure_ascii=False) if "error" not in r else r["error"])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
