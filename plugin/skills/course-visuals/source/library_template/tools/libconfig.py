"""This library's own settings, read from library_config.json beside tools/.

Every tool takes the library's name, its rights states and its paths from here, so the same tools
serve every subject. A path in library_config.json is either '{LIB}/...' (this folder, wherever it
sits), relative to this folder, or absolute (a folder on one person's computer).
"""
import json
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent
SHIP_DEFAULT = ("PUBLIC_DOMAIN", "ATTRIBUTION_REQUIRED", "CLEARED", "OWNER_CLEARED", "PROJECT_OWNED", "GENERATED")


def config():
    try:
        return json.loads((LIB / "library_config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CFG = config()
NAME = CFG.get("library_name") or LIB.name
REVIEWERS = CFG.get("reviewers") or "the library's owners"
SHIP_STATES = set(CFG.get("ship_states") or SHIP_DEFAULT)


def resolve(p):
    """A path from library_config.json as a Path, or None."""
    if not p:
        return None
    p = Path(str(p).replace("{LIB}", str(LIB)))
    return p if p.is_absolute() else LIB / p


def kb_hint():
    return ("this library's documents are not searchable yet - run: python tools/build_library.py "
            "--kb-builder <the factory's kb/builder/kb_build.py> (subject_library.py sync does it)")
