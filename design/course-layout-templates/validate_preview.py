"""Validate portable preview contracts/resources and deterministic generation.

Standard library only. This does not validate a production course sequence or
replace browser geometry and visual review.
"""
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "template-preview"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.slots = set()
        self.refs = []
        self.visuals = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "data-slot" in attrs:
            self.slots.add(attrs["data-slot"])
        if tag in ("svg", "canvas", "img"):
            self.visuals.append(tag)
        for key in ("src", "href"):
            if key in attrs:
                self.refs.append(attrs[key])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_resource(base, reference):
    if reference.startswith(("#", "data:")):
        return
    require(not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", reference, re.I),
            "External resource in portable specimen: " + reference)
    target = (base / reference.split("#", 1)[0].split("?", 1)[0]).resolve()
    require(ROOT == target or ROOT in target.parents, "Reference outside preview: " + reference)
    require(target.is_file(), "Missing resource: " + str(target))


def main():
    catalogue = json.loads((PACK / "catalog.json").read_text(encoding="utf-8"))
    ids = [entry["id"] for entry in catalogue]
    require(len(ids) == len(set(ids)), "Duplicate template IDs")
    require(set(ids) == {p.parent.name for p in (PACK / "templates").glob("*/template.json")},
            "Catalogue and contract directories differ")
    rules = json.loads((PACK / "course-layout-rules.json").read_text(encoding="utf-8"))
    require(rules["maxConsecutiveTextOnlySlides"] == 2, "Owner's sequence rule changed")
    require(rules["denseContentRequiresAdjacentVisual"] is True, "Dense visual requirement changed")
    require(rules["splitBalance"]["default"] == [0.55, 0.45], "Selected split changed")
    dense = 0
    for entry in catalogue:
        contract_path = PACK / entry["contract"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        page_path = PACK / entry["path"]
        require(contract["id"] == entry["id"] + ".v1", "Template ID/version mismatch")
        require(contract["entry"] == page_path.name, "Contract entry mismatch")
        page = Page()
        page.feed(page_path.read_text(encoding="utf-8"))
        required = {slot["name"] for slot in contract["slots"] if slot.get("required")}
        require(required <= page.slots, str(page_path) + ": missing slots " + str(required - page.slots))
        for ref in page.refs:
            local_resource(page_path.parent, ref)
        for ref in contract["assets"]:
            local_resource(contract_path.parent, ref)
        policy = contract["visualPolicy"]
        require(policy["maxConsecutiveTextOnlySlides"] == 2, "Template sequence policy mismatch")
        if policy["isDenseContent"]:
            dense += 1
            require(bool(page.visuals), "Dense specimen lacks a visual: " + entry["id"])
            require(contract["contentBalance"]["textShare"] == 0.55 and
                    contract["contentBalance"]["visualShare"] == 0.45,
                    "Dense balance metadata mismatch: " + entry["id"])
    gallery = Page()
    gallery.feed((ROOT / "preview.html").read_text(encoding="utf-8"))
    for ref in gallery.refs:
        local_resource(ROOT, ref)
    for css in (PACK / "assets").glob("*.css"):
        for ref in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", css.read_text(encoding="utf-8")):
            local_resource(css.parent, ref.strip())
    with tempfile.TemporaryDirectory(prefix="layout-preview-check-") as directory:
        generated = Path(directory)
        (generated / "assets").mkdir()
        for name in ("build_preview.py", "dense_templates.py"):
            shutil.copy2(PACK / name, generated / name)
        result = subprocess.run([sys.executable, "-B", str(generated / "build_preview.py")],
                                check=True, capture_output=True, text=True)
        require("Built" in result.stdout, "Generator did not complete")
        for file in generated.rglob("*"):
            if not file.is_file() or file.suffix == ".py":
                continue
            relative = file.relative_to(generated)
            require((PACK / relative).is_file(), "Missing generated file: " + str(relative))
            require(file.read_bytes() == (PACK / relative).read_bytes(),
                    "Stale generated file: " + str(relative) + "; run build_preview.py")
    print("PASS: %d templates, %d dense visuals, local assets/slots, owner policy metadata, deterministic regeneration."
          % (len(catalogue), dense))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print("FAIL:", error, file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        raise SystemExit(1)
