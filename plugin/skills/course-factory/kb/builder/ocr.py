# -*- coding: utf-8 -*-
"""Reading a scanned page with PyMuPDF's own Tesseract - no tesseract.exe, no picture file, the page never leaves memory.

The page is read whole (full=True: reading only the pictures loses text on real scans), at 200 dpi. A page that comes
out as garbage is tried turned a quarter, a half and three quarters (PyMuPDF has no orientation detection), and the
best reading by word quality is kept. The language is chosen per page by its own words (lang.py): English first, and a
page whose words are Latvian is read again with the Latvian model - an English page is never read with Latvian loaded.
"""
from __future__ import annotations

import os
import re

import lang as langmod
from structure import Line

MODELS = ("eng", "lav", "rus")
BUILDER_DIR = "COURSE_KB_BUILDER"
_TOKEN_OK = re.compile(r"^[\"'(\[]*([^\W\d_]{2,})[\"')\].,;:!?]*$", re.U)
_VOWEL = re.compile(r"[aeiouyāēīūůőöüäåøæаеёиоуыэюя]", re.I)
ROTATION_TRY_BELOW = 0.45       # word quality under which a page is tried turned
ROTATION_MIN_TOKENS = 20        # a page with fewer marks than this is not worth turning
TRY_DPI = 100                   # how large a turned page is drawn to see whether the turn reads better


def _models_in(folder):
    try:
        names = set(os.listdir(folder))
    except OSError:
        return set()
    return {m for m in MODELS if m + ".traineddata" in names}


def _ancestors(p):
    p = os.path.abspath(p)
    while True:
        yield p
        up = os.path.dirname(p)
        if up == p:
            return
        p = up


def _builder_tessdata(folder):
    """The Course KB Builder's own reading models: _runtime\\tesseract\\tessdata in the COURSE_KB_BUILDER folder,
    looked for as kb_tool.find_builder looks for the builder (named by NOVIKONTAS_KB_BUILDER, else beside the folder and
    up to four folders above it, then the Desktop, Documents and the home folder, one folder deep)."""
    tail = os.path.join("_runtime", "tesseract", "tessdata")
    named = os.environ.get("NOVIKONTAS_KB_BUILDER")
    if named:
        named = os.path.abspath(os.path.expanduser(named))
        if os.path.isfile(named):
            named = os.path.dirname(named)
        return [os.path.join(named, tail)]
    places = []
    for i, a in enumerate(_ancestors(folder or os.getcwd())):
        if i > 4:
            break
        places.append(os.path.join(a, BUILDER_DIR))
    home = os.path.expanduser("~")
    for base in (os.path.join(home, "Desktop"), os.path.join(home, "Documents"), home):
        places.append(os.path.join(base, BUILDER_DIR))
        if base != home and os.path.isdir(base):
            try:
                places += [os.path.join(base, n, BUILDER_DIR) for n in sorted(os.listdir(base))]
            except OSError:
                pass
    return [os.path.join(p, tail) for p in places if os.path.isdir(p)]


def find_tessdata(given=None, folder=None):
    """(folder, {models}) of the first place holding eng or lav reading models, or (None, set()). Looked for in this
    order: --tessdata, NOVIKONTAS_TESSDATA, TESSDATA_PREFIX, the Course KB Builder's own, %LOCALAPPDATA%\\NOVIKONTAS\\tessdata."""
    candidates = []
    if given:
        candidates.append(given)
    for var in ("NOVIKONTAS_TESSDATA", "TESSDATA_PREFIX"):
        if os.environ.get(var):
            candidates += [os.environ[var], os.path.join(os.environ[var], "tessdata")]
    candidates += _builder_tessdata(folder)
    local = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    candidates.append(os.path.join(local, "NOVIKONTAS", "tessdata"))
    for c in candidates:
        models = _models_in(c)
        if models & {"eng", "lav"}:
            return os.path.abspath(c), models
        if given and c == given:
            return None, set()          # a folder that is named is the only one used
    return None, set()


# The reading models, fetched when a run has a scanned page to read and they are not on this computer: tessdata_fast
# at a pinned commit (Apache-2.0), each checked by size and SHA-256 before it is used.
MODEL_URL = ("https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/"
             "87416418657359cb625c412a48b6e1d6d41c29bd/%s.traineddata")
MODEL_FILES = {
    "eng": (4113088, "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2", "English"),
    "lav": (2717247, "7d9eaf22254b381f18b806cd6cb647862a397a7221adbce3e22cc421793a8847", "Latvian"),
    "rus": (3861738, "e16e5e036cce1d9ec2b00063cf8b54472625b9e14d893a169e2b0dedeb4df225", "Russian"),
}


def local_tessdata():
    """Where fetched models are kept: %LOCALAPPDATA%\\NOVIKONTAS\\tessdata, or ~/.novikontas/tessdata elsewhere."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "NOVIKONTAS", "tessdata")
    return os.path.join(os.path.expanduser("~"), ".novikontas", "tessdata")


def model_ok(path, lang):
    """True when the file is the pinned model: right size and SHA-256."""
    import hashlib
    size, sha, _ = MODEL_FILES[lang]
    try:
        if os.path.getsize(path) != size:
            return False
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest() == sha
    except OSError:
        return False


def fetch_model(lang, folder, say=print, timeout=60):
    """Fetch one model into folder: written to <name>.part, renamed only after size and checksum match. True if it is
    there now. The base address can be changed with NOVIKONTAS_TESSDATA_URL (a %s for the language, or a folder URL)."""
    import urllib.request
    size, _, name = MODEL_FILES[lang]
    target = os.path.join(folder, lang + ".traineddata")
    if model_ok(target, lang):
        return True
    if os.environ.get("NOVIKONTAS_OFFLINE") == "1":
        return False
    base = os.environ.get("NOVIKONTAS_TESSDATA_URL") or MODEL_URL
    url = base % lang if "%s" in base else base.rstrip("/") + "/%s.traineddata" % lang
    say("Fetching the %s reading model (%.1f MB) ..." % (name, size / 1e6))
    part = target + ".part"
    try:
        os.makedirs(folder, exist_ok=True)
        with urllib.request.urlopen(url, timeout=timeout) as r, open(part, "wb") as f:
            while True:
                block = r.read(1 << 16)
                if not block:
                    break
                f.write(block)
    except Exception as e:                                   # noqa: BLE001 - no network is an ordinary case
        say("  not fetched (%s)" % (getattr(e, "reason", None) or e))
        _remove(part)
        return False
    if not model_ok(part, lang):
        say("  not used - the file fetched is not the expected one (size or checksum differs)")
        _remove(part)
        return False
    os.replace(part, target)
    return True


def _remove(p):
    try:
        os.remove(p)
    except OSError:
        pass


def ensure_tessdata(langs, given=None, folder=None, say=print):
    """(tessdata folder, {models}) holding every language in langs if it can be had: a place that already holds them
    all is used as it is; else the local folder gets them - copied from a place that has a verified copy, or fetched."""
    import shutil
    places = []
    if given:
        places.append(given)
    for var in ("NOVIKONTAS_TESSDATA", "TESSDATA_PREFIX"):
        if os.environ.get(var):
            places += [os.environ[var], os.path.join(os.environ[var], "tessdata")]
    places += _builder_tessdata(folder)
    local = local_tessdata()
    places.append(local)
    for p in places:
        if set(langs) <= _models_in(p):
            return os.path.abspath(p), _models_in(p)
    for lang in langs:
        target = os.path.join(local, lang + ".traineddata")
        if model_ok(target, lang):
            continue
        copied = False
        for p in places:
            src = os.path.join(p, lang + ".traineddata")
            if os.path.abspath(p) != os.path.abspath(local) and model_ok(src, lang):
                try:
                    os.makedirs(local, exist_ok=True)
                    shutil.copyfile(src, target + ".part")
                    os.replace(target + ".part", target)
                    copied = True
                    break
                except OSError:
                    _remove(target + ".part")
        if not copied:
            fetch_model(lang, local, say)
    have = _models_in(local)
    if have & {"eng", "lav"}:
        return local, have
    return find_tessdata(given, folder)


def word_quality(text):
    """The share of marks on the page that read as words (letters, a vowel). Garbage from a sideways page is mostly
    one-letter marks and symbols."""
    tokens = (text or "").split()
    if not tokens:
        return 0.0
    good = 0
    for t in tokens:
        m = _TOKEN_OK.match(t)
        if m and _VOWEL.search(m.group(1)):
            good += 1
    return good / len(tokens)


def _read(page, language, tessdata, dpi):
    """[[Line]] blocks and plain text of one OCR reading."""
    import pymupdf
    tp = page.get_textpage_ocr(language=language, dpi=dpi, full=True, tessdata=tessdata)
    raw = page.get_text("dict", textpage=tp, flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
    blocks, plain = [], []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines = []
        for line in block.get("lines", []):
            text = "".join(s.get("text", "") for s in line.get("spans", []))
            if text.strip():
                lines.append(Line(text))           # no font sizes: an OCR reading has none worth trusting
                plain.append(text)
        if lines:
            blocks.append(lines)
    return blocks, "\n".join(plain)


def first_language(prior, models, forced):
    """The model a page is read with first, or None when the one it needs is not on this computer (a Russian scan
    with no rus.traineddata: read with an English model it would only give garbage)."""
    if forced in ("eng", "lav", "rus"):
        if forced not in models:
            return None
        return "rus+eng" if forced == "rus" and "eng" in models else forced
    if prior == "rus":
        return ("rus+eng" if "eng" in models else "rus") if "rus" in models else None
    if prior == "lav" and "lav" in models:
        return "lav"
    return "eng" if "eng" in models else ("lav" if "lav" in models else None)


def read_scanned_page(page, tessdata, models, prior=None, forced=None, dpi=200):
    """{blocks, text, language, rotation, quality, note}: the best reading of one scanned page."""
    first = first_language(prior, models, forced)
    if first is None:
        return {"blocks": [], "text": "", "language": "", "rotation": 0, "quality": 0.0,
                "note": "needs rus.traineddata" if (forced == "rus" or prior == "rus") else "no reading model"}
    blocks, text = _read(page, first, tessdata, dpi)
    quality, rotation, note = word_quality(text), 0, ""
    if quality < ROTATION_TRY_BELOW and len(text.split()) >= ROTATION_MIN_TOKENS:
        # the turns are tried drawn small (fast); only the winning turn is read again at full size
        original = page.rotation
        best_q, best_turn = quality, 0
        try:
            for turn in (90, 180, 270):
                page.set_rotation((original + turn) % 360)
                q = word_quality(_read(page, first, tessdata, TRY_DPI)[1])
                if q > best_q:
                    best_q, best_turn = q, turn
            if best_turn and best_q >= quality + 0.15:
                page.set_rotation((original + best_turn) % 360)
                b, t = _read(page, first, tessdata, dpi)
                if word_quality(t) > quality:
                    quality, rotation, blocks, text = word_quality(t), best_turn, b, t
                    note = "read turned %d degrees" % rotation
        finally:
            page.set_rotation(original)
    used = first
    if (not forced or forced == "auto") and not first.startswith("rus"):
        found = langmod.lang_of(text)
        want = None
        first_shares = langmod.shares(text)
        if "rus" in models and first_shares["eng"] < 0.10 and first_shares["words"] >= 15:
            # a Russian scan read with a Latin model comes out as Latin look-alikes ("no" for "по"), never as Cyrillic:
            # so a page that is not plainly English is also read with the Russian model, and kept as Russian when
            # its Russian function words say so
            original = page.rotation
            try:
                if rotation:
                    page.set_rotation((original + rotation) % 360)
                rb, rt = _read(page, "rus", tessdata, dpi)
            finally:
                page.set_rotation(original)
            s = langmod.shares(rt)
            # measured on English figure and screen-shot pages: a Russian reading of them is Cyrillic noise (word
            # quality 0.03-0.44) that still holds one-letter "function words"; a real Russian page reads cleanly
            if (s["cyr"] > 0.5 and s["rus"] >= langmod.MIN_SHARE and s["words"] >= 15
                    and word_quality(rt) >= max(0.6, quality + 0.1)):
                found = "rus"
                if "eng" not in models:
                    blocks, text, used, quality, want = rb, rt, "rus", word_quality(rt), None
                    found = None
        if found == "lav" and first != "lav" and "lav" in models:
            want = "lav"
        elif found == "eng" and first != "eng" and "eng" in models:
            want = "eng"
        elif found == "mixed" and {"eng", "lav"} <= models:
            want = "lav+eng"
        elif found == "rus":
            if "rus" in models:
                want = "rus+eng" if "eng" in models else "rus"
            else:
                note = (note + "; " if note else "") + "Russian text - no rus.traineddata on this computer"
        if want:
            original = page.rotation
            try:
                if rotation:
                    page.set_rotation((original + rotation) % 360)
                blocks, text = _read(page, want, tessdata, dpi)
            finally:
                page.set_rotation(original)
            used, quality = want, word_quality(text)
    return {"blocks": blocks, "text": text, "language": used, "rotation": rotation, "quality": round(quality, 3),
            "note": note}
