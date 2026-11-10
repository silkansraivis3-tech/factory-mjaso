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


def grey_copy(page, dpi):
    """(document, page): the page drawn as one grey picture on an upright page of the same size.

    The OCR reads this copy, never the page itself. Measured on gas-basic's "LNG Shipping Knowledge.pdf" (every page
    stored turned 270 degrees): read as they are, those pages lose whole paragraphs - page 15 gave 334 characters, its
    copy 1 849 - and the IMO model course covers read as nothing at all."""
    import pymupdf
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
    doc = pymupdf.open()
    copy = doc.new_page(width=page.rect.width, height=page.rect.height)
    copy.insert_image(copy.rect, pixmap=pix)
    return doc, copy


def _word_lines(words):
    """Lines from the OCR's words, a line cut where two words stand much further apart than a space: Tesseract joins
    the lines of two columns that sit level ("the walls of the | Behaviour of CO2")."""
    import statistics
    by = {}
    for w in words:
        by.setdefault((w[5], w[6]), []).append(w)
    blocks = {}
    for key in sorted(by):
        ws = sorted(by[key], key=lambda w: w[0])
        height = statistics.median([w[3] - w[1] for w in ws]) or 5.0
        cur = [ws[0]]
        runs = []
        for w in ws[1:]:
            if w[0] - cur[-1][2] > GAP_CUT * height:
                runs.append(cur)
                cur = [w]
            else:
                cur.append(w)
        runs.append(cur)
        for run in runs:
            blocks.setdefault(key[0], []).append(Line(" ".join(w[4] for w in run), 0.0, False, min(w[0] for w in run),
                                                      min(w[1] for w in run), max(w[2] for w in run),
                                                      max(w[3] for w in run)))
    return [blocks[k] for k in sorted(blocks)]


GAP_CUT = 1.5                    # a gap wider than this many letter heights ends a line


def _ocr_words(page, language, tessdata, dpi, clip=None):
    """The words of one OCR reading of a grey copy of the page (or of one region of it), in page coordinates."""
    import pymupdf
    if clip is None:
        doc, copy = grey_copy(page, dpi)
        dx = dy = 0.0
    else:
        pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False, clip=clip)
        doc = pymupdf.open()
        copy = doc.new_page(width=clip.width, height=clip.height)
        copy.insert_image(copy.rect, pixmap=pix)
        dx, dy = clip.x0, clip.y0
    try:
        tp = copy.get_textpage_ocr(language=language, dpi=dpi, full=True, tessdata=tessdata)
        words = copy.get_text("words", textpage=tp)
    finally:
        doc.close()
    return [(w[0] + dx, w[1] + dy, w[2] + dx, w[3] + dy) + tuple(w[4:]) for w in words]


def _blocks_of(words):
    """Blocks in reading order: the reading's own, with the blocks read again region by region put where they sit on
    the page (before the first block that starts below them); a page in columns is read column by column."""
    from structure import reflow_columns
    first = [w for w in words if w[5] < 1000]
    again = [w for w in words if w[5] >= 1000]
    blocks = _word_lines(first)
    for extra in _word_lines(again):
        top = min(l.y0 for l in extra)
        at = next((i for i, b in enumerate(blocks) if min(l.y0 for l in b) > top), len(blocks))
        blocks.insert(at, extra)
    flowed, columns = reflow_columns(blocks)
    return flowed if columns > 1 else blocks


def _read(page, language, tessdata, dpi):
    """([[Line]] blocks, plain text, words) of one OCR reading of a grey copy of the page, columns read one by one."""
    words = _ocr_words(page, language, tessdata, dpi)
    blocks = _blocks_of(words)
    return blocks, "\n".join(l.text for b in blocks for l in b), words


# ------------------------------------------------------------------ is the reading complete? (no reference needed)
INK_DPI, INK_CELL = 75, 12      # the page drawn at 75 dpi, judged in squares of 12 pixels (about 11.5 points)
LOW_COVER = 0.40                # a reading whose words cover less of the page's print than this is incomplete
MIN_PRINT_CELLS = 40            # fewer squares of print than this: too little print to judge
# ... and fewer characters read than this many per square of print. Measured on gas-basic (1 090 OCR pages): pages
# under the cover limit that hold 4-37 characters a square were read as fully as the .exe read them (figure-rich
# pages whose drawings count as print); the readings that lost paragraphs had 0.6-2.9
LOW_CHARS_PER_CELL = 3.0


def print_cells(page):
    """[(x, y)] of the squares of the page that look like print: some dark, thin strokes (many short dark runs, few
    long ones). Photographs and solid areas mostly fail the test. Measured: well-read pages have 55-100 % of these
    squares under a recognised word, the readings that lost paragraphs 0-26 %."""
    import pymupdf
    pix = page.get_pixmap(dpi=INK_DPI, colorspace=pymupdf.csGRAY, alpha=False)
    w, h = pix.width, pix.height
    b = pix.samples.translate(bytes(1 if v < 140 else 0 for v in range(256)))
    size, out = INK_CELL, []
    for cy in range(0, h - size + 1, size):
        for cx in range(0, w - size + 1, size):
            dark = short = long_ = 0
            for y in range(cy, cy + size):
                row = b[y * w + cx: y * w + cx + size]
                dark += row.count(1)
                for run in row.split(b"\x00"):
                    if run:
                        if len(run) <= 4:
                            short += 1
                        else:
                            long_ += 1
            share = dark / float(size * size)
            if 0.06 <= share <= 0.45 and short >= 8 and long_ <= short // 2:
                out.append((cx * 72.0 / INK_DPI, cy * 72.0 / INK_DPI))
    return out


def _real_word(w):
    """A word that reads as one (letters with a vowel, or a number) - noise read off a figure covers nothing."""
    t = w[4]
    if re.match(r"^[\(\[]?[\d.,%°/:-]+[\)\]]?[.,;:]?$", t) and sum(ch.isdigit() for ch in t) >= 2:
        return True
    m = _TOKEN_OK.match(t)
    # three letters at least: noise off a picture is mostly one- and two-letter marks ("SO", "aS", "ie")
    return bool(m and len(m.group(1)) >= 3 and _VOWEL.search(m.group(1)))


def _uncovered(cells, words, pad=2.0):
    side = INK_CELL * 72.0 / INK_DPI
    words = [w for w in words if _real_word(w)]
    out = []
    for x, y in cells:
        cx, cy = x + side / 2, y + side / 2
        if not any(w[0] - pad <= cx <= w[2] + pad and w[1] - pad <= cy <= w[3] + pad for w in words):
            out.append((x, y))
    return out


def _regions(cells):
    """Rectangles around groups of neighbouring squares (the print a reading missed), biggest first."""
    import pymupdf
    side = INK_CELL * 72.0 / INK_DPI
    left = {(round(x / side), round(y / side)) for x, y in cells}
    groups = []
    while left:
        stack, group = [left.pop()], []
        while stack:
            c = stack.pop()
            group.append(c)
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-1, 0, 1):
                    n = (c[0] + dx, c[1] + dy)
                    if n in left:
                        left.remove(n)
                        stack.append(n)
        if len(group) >= 6:
            xs, ys = [g[0] for g in group], [g[1] for g in group]
            groups.append((len(group), pymupdf.Rect((min(xs) - 1) * side, (min(ys) - 1) * side,
                                                    (max(xs) + 2) * side, (max(ys) + 2) * side)))
    return [r for _, r in sorted(groups, key=lambda g: -g[0])][:6]


def complete_reading(page, language, tessdata, words, dpi):
    """(words, cover, print squares): a reading made complete where it can be. The print the words do not cover is
    read again region by region (each clipped and drawn at 300 dpi), and the new words are added where no word is."""
    cells = print_cells(page)
    if len(cells) < MIN_PRINT_CELLS:
        return words, 1.0, len(cells)
    missed = _uncovered(cells, words)
    cover = 1.0 - len(missed) / float(len(cells))
    if len(missed) >= 6 and cover < 0.9:
        added = list(words)
        for k, rect in enumerate(_regions(missed)):
            rect = rect & page.rect
            if rect.is_empty or rect.width < 20 or rect.height < 8:
                continue
            for w in _ocr_words(page, language, tessdata, max(dpi, 300), clip=rect):
                cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
                if not any(o[0] <= cx <= o[2] and o[1] <= cy <= o[3] for o in words):
                    added.append(w[:5] + (1000 + 100 * k + w[5],) + tuple(w[6:]))
        missed = _uncovered(cells, added)
        cover, words = 1.0 - len(missed) / float(len(cells)), added
    return words, round(cover, 3), len(cells)


def _read_full(page, language, tessdata, dpi):
    """One reading, completed region by region: (blocks, text, words, cover, print squares)."""
    words = _ocr_words(page, language, tessdata, dpi)
    words, cover, cells = complete_reading(page, language, tessdata, words, dpi)
    blocks = _blocks_of(words)
    return blocks, "\n".join(l.text for b in blocks for l in b), words, cover, cells


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
    """{blocks, text, language, rotation, quality, note, cover, print_cells, low}: the best reading of one scanned
    page, made complete region by region (complete_reading). low = its words still cover less than LOW_COVER of the
    page's print, after a second reading at 300 dpi - the page may be read incompletely and is reported so."""
    first = first_language(prior, models, forced)
    if first is None:
        return {"blocks": [], "text": "", "language": "", "rotation": 0, "quality": 0.0, "cover": 0.0,
                "print_cells": 0, "low": False,
                "note": "needs rus.traineddata" if (forced == "rus" or prior == "rus") else "no reading model"}
    blocks, text, words = _read(page, first, tessdata, dpi)
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
                b, t, w = _read(page, first, tessdata, dpi)
                if word_quality(t) > quality:
                    quality, rotation, blocks, text, words = word_quality(t), best_turn, b, t, w
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
                rb, rt, rw = _read(page, "rus", tessdata, dpi)
            finally:
                page.set_rotation(original)
            s = langmod.shares(rt)
            # measured on English figure and screen-shot pages: a Russian reading of them is Cyrillic noise (word
            # quality 0.03-0.44) that still holds one-letter "function words"; a real Russian page reads cleanly
            if (s["cyr"] > 0.5 and s["rus"] >= langmod.MIN_SHARE and s["words"] >= 15
                    and word_quality(rt) >= max(0.6, quality + 0.1)):
                found = "rus"
                if "eng" not in models:
                    blocks, text, words, used, quality, want = rb, rt, rw, "rus", word_quality(rt), None
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
                blocks, text, words = _read(page, want, tessdata, dpi)
            finally:
                page.set_rotation(original)
            used, quality = want, word_quality(text)
    # complete the reading: the print its words do not cover is read again region by region; still too little
    # covered, the whole page is read once more at 300 dpi and the better reading kept
    original = page.rotation
    try:
        if rotation:
            page.set_rotation((original + rotation) % 360)
        words, cover, cells = complete_reading(page, used, tessdata, words, dpi)
        read_chars = sum(len(w[4]) for w in words)
        if cover < LOW_COVER and dpi < 300 and read_chars < LOW_CHARS_PER_CELL * cells:
            w2 = _ocr_words(page, used, tessdata, 300)
            w2, c2, _ = complete_reading(page, used, tessdata, w2, 300)
            if c2 > cover:
                words, cover = w2, c2
                note = (note + "; " if note else "") + "read again at 300 dpi"
    finally:
        page.set_rotation(original)
    blocks = _blocks_of(words)
    text = "\n".join(l.text for b in blocks for l in b)
    chars = len("".join(text.split()))
    return {"blocks": blocks, "text": text, "language": used, "rotation": rotation, "quality": round(word_quality(text), 3),
            "note": note, "cover": cover, "print_cells": cells,
            "low": cells >= MIN_PRINT_CELLS and cover < LOW_COVER and chars < LOW_CHARS_PER_CELL * cells}
