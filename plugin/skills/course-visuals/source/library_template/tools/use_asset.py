"""Put a library asset into a course module, with its provenance.

    python tools/use_asset.py <asset id> "<course>/modules/module11" --as m11_<name>.jpg --note "M11 slide s07"
    python tools/use_asset.py --find <word>            # list matching asset ids first

Tablets need every module to be self-contained, so the course keeps its own copy. This script copies the
library file into <module>/assets/img (photos, renders) or <module>/assets/fig (figures), and writes the
library's provenance record into that folder's _photo_meta.json / _figure_meta.json with
"library_id" and "library_sha256", so the next build_library.py run links the use back to the library.
It never overwrites a different file of the same name.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import libconfig as C  # noqa: E402

LIB = C.LIB
TARGET = {"photo": ("img", "_photo_meta.json"), "render": ("img", "_photo_meta.json"),
          "figure": ("fig", "_figure_meta.json"), "sim": ("sim", "_sim_meta.json")}


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("asset_id", nargs="?")
    ap.add_argument("module", nargs="?", help="the module folder, e.g. .../course/modules/module11")
    ap.add_argument("--as", dest="name", help="file name inside the course (default: <asset_id><ext>)")
    ap.add_argument("--note", default="", help="where it is used, e.g. 'M11 slide s07'")
    ap.add_argument("--find", help="search asset ids, descriptions and topics")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    reg = LIB / "assets" / "ASSETS.json"
    assets = json.loads(reg.read_text(encoding="utf-8")).get("assets", []) if reg.exists() else []

    if args.find:
        q = args.find.lower()
        for a in assets:
            blob = f"{a['id']} {a.get('description') or ''} {' '.join(a.get('topics', []))}".lower()
            if q in blob:
                print(f"{a['id']:45} {a['kind']:7} {a['rights_state']:22} {', '.join(a.get('courses', []))}")
        return 0
    if not (args.asset_id and args.module):
        ap.error("give an asset id and a module folder, or --find")

    a = next((x for x in assets if x["id"] == args.asset_id), None)
    if not a:
        sys.exit(f"no asset '{args.asset_id}' in {C.NAME} - try --find")
    if a["rights_state"] not in C.SHIP_STATES:
        print(f"! rights state is {a['rights_state']} - classroom reference only; see CHECKS.md before it ships on the tablets")
    if a["ai_generated"]:
        print("! AI-generated - never use it as a picture of equipment a trainee must recognise")

    src = LIB / a["file"]
    sub, meta_name = TARGET[a["kind"]]
    folder = Path(args.module) / "assets" / sub
    folder.mkdir(parents=True, exist_ok=True)
    name = args.name or Path(a["file"]).name
    dest = folder / name
    if dest.exists() and sha256(dest) != a["sha256"]:
        sys.exit(f"{dest} exists and is a different file - choose another --as name")
    shutil.copy2(src, dest)

    meta_path = folder / meta_name
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    record = dict(a.get("_full_meta") or {})
    record.update({"library_id": a["id"], "library_sha256": a["sha256"], "library": C.NAME,
                   "rights_state": a["rights_state"], "used_in": args.note or record.get("used_in", "")})
    meta[name] = record
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"copied {a['id']} -> {dest}\nprovenance written to {meta_path}")
    if a["rights_state"] == "ATTRIBUTION_REQUIRED":
        print(f"credit on the slide: {a.get('credit')} - {a.get('licence')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
