# -*- coding: utf-8 -*-
"""Which language a page is written in, from its own words - English, Latvian or Russian.

Not from the OCR engine's confidence: a Latvian page read as English scores higher confidence than a real English
page. Function words survive a wrong reading once the Latvian accents are folded away (an English reading of
"drošības" gives "drosibas"), so they tell the languages apart.
"""
from __future__ import annotations

import re

EN = set("the and of to in is for be are with on that by as or this from shall should which an at it not".split())
LV = set("un ar uz par ir lai vai kas no pie tiek ka tas ta ja pec ari bet kuru kuri ko var nav kursa saskana".split())
RU = set("и в на с по для не что из к от как или это при должны быть".split())
# stop words of the three languages (the search side uses them from index version 6; version 5 keeps the
# Course Source Processor's English list, so a v5 index reads the same with every reader)
STOP = {
    "eng": set("a an and are as at be been but by can for from had has have if in into is it its may must not of on or "
               "shall should such than that the their them then there these those to was were when which will with "
               "would you your".split()),
    "lav": set("un ar uz par no ir lai vai kas kā to tā pie pēc arī bet jo ja nav tiek var būt".split()),
    "rus": set("и в на с по для не что из к от как или это при".split()),
}
HEADING_WORDS = {
    "eng": ("annex", "appendix", "chapter", "section", "module", "part", "unit"),
    "lav": ("pielikums", "nodaļa", "sadaļa", "modulis", "daļa", "tēma"),
    "rus": ("приложение", "глава", "раздел", "модуль", "часть", "тема"),
}
_FOLD = str.maketrans("āčēģīķļņšūžĀČĒĢĪĶĻŅŠŪŽёЁ", "acegiklnsuzACEGIKLNSUZеЕ")
_WORD = re.compile(r"[^\W\d_]+", re.U)
MIN_SHARE = 0.04


def fold(text):
    return (text or "").translate(_FOLD)


def shares(text):
    """{eng, lav, rus, cyr, words}: the share of each language's function words, and of Cyrillic letters."""
    words = _WORD.findall(fold(text).lower())
    letters = sum(ch.isalpha() for ch in text or "") or 1
    cyr = sum(1 for ch in text or "" if "Ѐ" <= ch <= "ӿ") / letters
    n = len(words) or 1
    return {"eng": sum(w in EN for w in words) / n, "lav": sum(w in LV for w in words) / n,
            "rus": sum(w in RU for w in words) / n, "cyr": cyr, "words": len(words)}


def lang_of(text):
    """'eng', 'lav', 'rus', 'mixed' or None (too few words to say)."""
    s = shares(text)
    if s["words"] < 15:
        return None
    if s["cyr"] > 0.3:
        return "rus"
    eng, lav = s["eng"], s["lav"]
    if eng >= MIN_SHARE and lav >= MIN_SHARE and min(eng, lav) / max(eng, lav) >= 0.5:
        return "mixed"
    best = "eng" if eng >= lav else "lav"
    return best if s[best] >= MIN_SHARE else None


def lang_of_name(name):
    """A hint from a file name: Latvian letters or words in it."""
    low = (name or "").lower()
    if re.search(r"[āčēģīķļņšūž]", low) or re.search(r"(^|[^a-z])(lv|lav|latv)([^a-z]|$)", low):
        return "lav"
    return None
