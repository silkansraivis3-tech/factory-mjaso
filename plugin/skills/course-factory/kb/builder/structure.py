# -*- coding: utf-8 -*-
"""Headings, columns and paragraphs from typography and plain text patterns - never from meaning.

Ported from the Course Source Processor (csp/structure.py): the column reflow, the heading rules and the paragraph
assembly are the owner's, measured on the real corpus. Added here: Latvian and Russian heading words, a running header
that names a page ("Annex, page 4") is never a heading, a number alone on its line joins the heading after it
("4.1" + "Goal" -> "4.1 Goal"), and a line-end hyphen is kept where the hyphenated word is a real one ("LNG-fuelled").
Same input, same output.
"""
from __future__ import annotations

import re
from collections import Counter

BULLET_PREFIXES = ("-", "*", "•", "●", "▪", "–", "—", "o ", "> ")
_NUMBERED = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,3})[.)]?\s+(\S.*)$")
_NUMBER_ONLY = re.compile(r"^\d{1,2}(?:\.\d{1,2}){0,3}\.?$")
_DOT_ITEM = re.compile(r"^\.\d{1,2}(\s|$)")
_APPENDIX = re.compile(r"^(annex|appendix|chapter|section|module|part|unit|pielikums|nodaļa|sadaļa|modulis|daļa|tēma"
                       r"|приложение|глава|раздел|модуль|часть|тема)\b[\s:]*", re.IGNORECASE)
_NAMES_PAGE = re.compile(r"\b(page|lpp|lappuse|страница|стр)\.?\s*\d", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?;:,]$")
# a line-end hyphen: the ASCII one, the Unicode hyphen, or the soft hyphen many PDF makers write there
_HYPHEN_BREAK = re.compile(r"([^\W\d_])[-‐­]$", re.UNICODE)
_LAST_WORD = re.compile(r"([^\W_]+)[-‐­]$", re.UNICODE)
_FIRST_WORD = re.compile(r"^([^\W_]+)", re.UNICODE)
_WS = re.compile(r"[ \t ]+")
_WORD3 = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
HYPHENATED = re.compile(r"\b[^\W_]+(?:[-‐­][^\W_]+)+\b", re.UNICODE)


class Line(object):
    __slots__ = ("text", "size", "bold", "x0", "y0", "x1", "y1")

    def __init__(self, text, size=0.0, bold=False, x0=0.0, y0=0.0, x1=0.0, y1=0.0):
        self.text, self.size, self.bold = text, size, bold
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1


# ------------------------------------------------------------------ body text size
def body_font_size(pages_lines):
    """The most common font size, weighted by characters (0.0 if unknown)."""
    weights = Counter()
    for lines in pages_lines:
        for line in lines:
            if line.size > 0:
                weights[round(line.size * 2) / 2] += len(line.text)
    return float(weights.most_common(1)[0][0]) if weights else 0.0


def big_heading_sizes(pages_lines, body_size):
    """Distinct font sizes larger than the body, biggest first (three kept)."""
    if body_size <= 0:
        return []
    sizes = Counter()
    for lines in pages_lines:
        for line in lines:
            if line.size >= body_size * 1.15 and line.text.strip():
                sizes[round(line.size * 2) / 2] += 1
    return sorted(sizes.keys(), reverse=True)[:3]


# ------------------------------------------------------------------ columns
# A column boundary is only accepted where a vertical strip of the page is crossed by no line at all, and several
# lines end just before it and start just after it. Single-column prose never has such a strip, so ordinary pages
# are left exactly as they were.
_MIN_GUTTER_PT = 2.0
_GUTTER_RESOLUTION = 0.25
_SUPPORT_WINDOW_PT = 14.0
_MIN_SUPPORT = 2
_MIN_LINES_FOR_COLUMNS = 8
_MIN_COLUMN_SHARE = 0.12


def find_column_gaps(lines):
    spans = [(l.x0, l.x1) for l in lines if l.x1 > l.x0]
    if len(spans) < _MIN_LINES_FOR_COLUMNS:
        return []
    left = min(x0 for x0, _ in spans)
    right = max(x1 for _, x1 in spans)
    if right - left < 100:
        return []
    step = _GUTTER_RESOLUTION
    width = int((right - left) / step) + 2
    occupancy = bytearray(width)
    for x0, x1 in spans:
        start = max(0, int((x0 - left) / step))
        end = min(width - 1, int((x1 - left) / step))
        for i in range(start, end + 1):
            if occupancy[i] < 255:
                occupancy[i] += 1
    ends = [x1 for _, x1 in spans]
    starts = [x0 for x0, _ in spans]
    gaps, run_start = [], None
    for i in range(width):
        if occupancy[i] == 0:
            if run_start is None:
                run_start = i
        else:
            if run_start is not None:
                low, high = left + run_start * step, left + i * step
                if high - low >= _MIN_GUTTER_PT and _supported(low, high, ends, starts):
                    gaps.append((low + high) / 2.0)
            run_start = None
    return gaps


def _supported(low, high, ends, starts):
    before = sum(1 for x in ends if low - _SUPPORT_WINDOW_PT <= x <= low + 1.0)
    after = sum(1 for x in starts if high - 1.0 <= x <= high + _SUPPORT_WINDOW_PT)
    return before >= _MIN_SUPPORT and after >= _MIN_SUPPORT


def split_into_columns(lines):
    if not any(l.x1 > l.x0 for l in lines) or len(lines) < _MIN_LINES_FOR_COLUMNS:
        return [lines]
    gaps = find_column_gaps(lines)
    if not gaps:
        return [lines]

    def assign(boundaries):
        groups = [[] for _ in range(len(boundaries) + 1)]
        for line in lines:
            middle = (line.x0 + line.x1) / 2.0 if line.x1 > line.x0 else line.x0
            i = 0
            while i < len(boundaries) and middle > boundaries[i]:
                i += 1
            groups[i].append(line)
        return groups

    floor = max(4, int(len(lines) * _MIN_COLUMN_SHARE))
    boundaries, changed = list(gaps), True
    while boundaries and changed:
        changed = False
        for position, group in enumerate(assign(boundaries)):
            if len(group) < floor:
                del boundaries[min(position, len(boundaries) - 1)]
                changed = True
                break
    if not boundaries:
        return [lines]
    return [g for g in assign(boundaries) if g]


def lines_to_blocks(lines):
    """Paragraph blocks from loose lines, cut where the vertical gap is clearly larger than the page's usual one."""
    ordered = sorted(lines, key=lambda l: (round(l.y0, 1), l.x0))
    gaps = [max(0.0, ordered[i + 1].y0 - ordered[i].y1) for i in range(len(ordered) - 1)]
    positive = sorted(g for g in gaps if g > 0)
    median = positive[len(positive) // 2] if positive else 0.0
    limit = max(2.0, median + 1.5)
    blocks, current = [], []
    for i, line in enumerate(ordered):
        if current and gaps and i > 0 and gaps[i - 1] > limit:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def reflow_columns(blocks):
    """(blocks, column count): a columnar page re-ordered column by column; any other page untouched."""
    lines = [line for block in blocks for line in block]
    columns = split_into_columns(lines)
    if len(columns) < 2:
        return blocks, 1
    out = []
    for column in columns:
        out.extend(lines_to_blocks(column))
    return out, len(columns)


# ------------------------------------------------------------------ headings
def looks_like_bullet(text):
    return text.startswith(BULLET_PREFIXES) or bool(_DOT_ITEM.match(text))


def numbered_level(text):
    match = _NUMBERED.match(text)
    if not match:
        return None
    number, rest = match.groups()
    if len(text) > 110 or _SENTENCE_END.search(text) or not rest[:1].isupper() or ". " in rest:
        return None
    if len(text) > 60 and ", " in rest:
        return None                  # a numbered instruction ("1. On the diagram (see page 216), click"), not a title
    return min(number.count(".") + 1, 4)


def plausible_heading_text(text):
    stripped = text.strip()
    if not _WORD3.search(stripped) or ". " in stripped:
        return False
    dense = [ch for ch in stripped if not ch.isspace()]
    if not dense or sum(1 for ch in dense if ch.isalpha()) / len(dense) < 0.55:
        return False
    first = stripped[0]
    return first.isupper() or first.isdigit() or first in "(§"


def classify_line(line, body_size, big_sizes, tabular=False):
    """A heading level (1-4) or None. On a columnar page only numbered and named headings count."""
    text = line.text.strip()
    if len(text) < 2 or len(text) > 140 or looks_like_bullet(text) or not any(ch.isalpha() for ch in text):
        return None
    level = numbered_level(text)
    if level is not None:
        return level
    if _APPENDIX.match(text) and len(text) <= 90 and not _SENTENCE_END.search(text):
        # "Annex, page 4" is a running header that names its page - never a chapter heading
        return None if _NAMES_PAGE.search(text) else 1
    if tabular or not plausible_heading_text(text):
        return None
    if body_size > 0 and line.size >= body_size * 1.15 and not _SENTENCE_END.search(text):
        for rank, size in enumerate(big_sizes[:3]):
            if abs(line.size - size) < 0.25:
                return rank + 1
        return 3
    letters = [ch for ch in text if ch.isalpha()]
    if letters and all(ch.isupper() for ch in letters) and len(text) <= 80:
        if len(text.split()) <= 12 and not _SENTENCE_END.search(text):
            return 2
    if line.bold and len(text) <= 90 and not _SENTENCE_END.search(text):
        if body_size <= 0 or line.size >= body_size * 0.98:
            return 3
    return None


def join_number_headings(block, body_size=0.0, big_sizes=(), tabular=False):
    """A heading number alone on its line joins the title line after it: "4.1" + "Goal" -> "4.1 Goal". Only when the
    title line is a heading by its own type (bold, larger, capitals) - the first line of a numbered paragraph
    ("2.2.3" + "Although storage tanks are ...") stays text."""
    out, i = [], 0
    while i < len(block):
        line = block[i]
        if i + 1 < len(block) and _NUMBER_ONLY.match(line.text.strip()):
            nxt = block[i + 1]
            title = nxt.text.strip()
            if (title[:1].isupper() and len(title) <= 100 and not _SENTENCE_END.search(title)
                    and classify_line(nxt, body_size, list(big_sizes), tabular) is not None):
                out.append(Line(line.text.strip().rstrip(".") + " " + title, nxt.size, nxt.bold,
                                min(line.x0, nxt.x0), min(line.y0, nxt.y0), max(line.x1, nxt.x1), max(line.y1, nxt.y1)))
                i += 2
                continue
        out.append(line)
        i += 1
    return out


# ------------------------------------------------------------------ paragraphs
def hyphen_vocabulary(text):
    """Hyphenated words a document uses (lower case) - a line-end hyphen in one of them is kept."""
    return {re.sub("[‐­]", "-", m.group(0).lower()) for m in HYPHENATED.finditer(text or "")}


def join_two(previous, nxt, dehyphenate=True, vocab=None):
    """Two wrapped lines joined. A line-end hyphen is dropped ("pump-" + "room" -> "pumproom") unless the word before
    it is upper case or holds a digit ("LNG-fuelled") or the document writes the hyphenated word elsewhere
    ("low-flashpoint"). Any script: the letter tests are Unicode, so a Cyrillic word joins the same way."""
    if dehyphenate and _HYPHEN_BREAK.search(previous) and nxt[:1].islower():
        left = _LAST_WORD.search(previous)
        right = _FIRST_WORD.match(nxt)
        left_word = left.group(1) if left else ""
        keep = previous[:-1] + "-" + nxt
        if left_word and (left_word.isupper() or len(left_word) == 1 or any(ch.isdigit() for ch in left_word)):
            return keep                                 # "LNG-" + "fuelled", "k-" + "ε": the hyphen is part of the word
        if vocab and left_word and right and (left_word + "-" + right.group(1)).lower() in vocab:
            return keep                                 # "low-" + "flashpoint", written so elsewhere in the document
        return previous[:-1] + nxt
    return previous + " " + nxt


def assemble_paragraph(lines, dehyphenate=True, vocab=None):
    """Join wrapped lines into one paragraph; list items keep their own line."""
    out = []
    for raw in lines:
        text = _WS.sub(" ", raw).strip()
        if not text:
            continue
        if not out or looks_like_bullet(text) or numbered_level(text) is not None:
            out.append(text)
            continue
        previous = out[-1]
        if looks_like_bullet(previous) or numbered_level(previous) is not None:
            if _SENTENCE_END.search(previous) or not text[:1].islower():
                out.append(text)
                continue
        out[-1] = join_two(previous, text, dehyphenate, vocab)
    return "\n".join(out)


def build_page_text(blocks, body_size, big_sizes, tabular=False, vocab=None, dehyphenate=True):
    """(page text, [(heading, level)]). Blocks are separated by a blank line; headings are blocks of their own,
    written '#' * (level + 2), because "# Source" and "## Page N" own the top two levels of document.md.
    A block may also be a ready string (a table marker): it is kept as it is."""
    out_blocks, headings = [], []
    for block in blocks:
        if isinstance(block, str):
            out_blocks.append(block)
            continue
        pending = []
        lines = join_number_headings(block, body_size, big_sizes, tabular)
        for k, line in enumerate(lines):
            text = _WS.sub(" ", line.text).strip()
            if not text:
                continue
            level = classify_line(Line(text, line.size, line.bold), body_size, big_sizes, tabular=tabular)
            if level is not None and k + 1 < len(lines) and lines[k + 1].text.strip()[:1].islower() \
                    and not text.endswith((":", ".")) and (line.size <= 0 or abs(lines[k + 1].size - line.size) < 0.25):
                level = None                 # the first line of a wrapped paragraph ("2.2.3 Although tanks are ... of")
            if level is not None:
                if pending:
                    paragraph = assemble_paragraph(pending, dehyphenate, vocab)
                    if paragraph:
                        out_blocks.append(paragraph)
                    pending = []
                level = min(level, 4)
                out_blocks.append("#" * (level + 2) + " " + text)
                headings.append((text, level))
            else:
                pending.append(text)
        if pending:
            paragraph = assemble_paragraph(pending, dehyphenate, vocab)
            if paragraph:
                out_blocks.append(paragraph)

    # a block that clearly continues the previous sentence is joined to it
    merged = []
    for block in out_blocks:
        if (merged and not block.startswith("#") and not merged[-1].startswith("#") and not block.startswith("[[")
                and not merged[-1].startswith("[[") and not looks_like_bullet(block) and numbered_level(block) is None
                and block[:1].islower() and not _SENTENCE_END.search(merged[-1].split("\n")[-1])):
            merged[-1] = join_two(merged[-1], block, dehyphenate, vocab)
        else:
            merged.append(block)
    return "\n\n".join(merged).strip(), headings
