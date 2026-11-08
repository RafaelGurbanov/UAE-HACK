"""Language detection, Arabic/English normalisation and tokenising.

`normalize_for_match` is used by both BM25 and the citation checker, so a quote
counts as "exact" when it matches after whitespace, punctuation-quote, Arabic
diacritic/tatweel, alef/ya/ta-marbuta and digit normalisation, nothing looser.
"""

from __future__ import annotations

import re
import unicodedata

_AR = re.compile(r"[؀-ۿ]")
_LAT = re.compile(r"[A-Za-z]")
_AR_MARKS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # harakat, Quranic marks, tatweel
_QUOTES = re.compile(r"[\"'`«»“”„‘’‚‹›]")
_WS = re.compile(r"\s+")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_EN_STOP = set(
    "a an the of to in on for and or by with is are be as at from that this these those it its can may must shall "
    "what which who whom whose when where how why do does did not no any all such than then there their "
    "need needs first ok okay please tell me about would could should we our you your i my us get also just".split()
)
_AR_STOP = set("في من على الى إلى عن ان أن او أو ما هل مع هذا هذه ذلك تلك التي الذي التى كل هي هو ماذا كيف متى لماذا يجب يمكن".split())
_AZ_STOP = set("və ve ilə ile üçün bu bir hansı nə ne necə mi mı mu mü olan olar olur edir lazım lazımdır varmı da də ki".split())


_AZ_LETTERS = re.compile(r"[əƏğĞıİşŞçÇöÖüÜ]")
_AZ_WORDS = re.compile(r"\b(və|üçün|necə|hansı|nədir|uşaq\w*|məlumat\w*|razılıq\w*|qanun\w*|salam|olar|edir|lazımdır|varmı)\b", re.I)


def detect_language(text: str) -> str:
    """'ar' when Arabic letters outnumber Latin ones, else 'en'. (LLM mode: en/ar only.)"""
    return "ar" if len(_AR.findall(text)) > len(_LAT.findall(text)) else "en"


def detect_query_language(text: str) -> str:
    """en / ar / az. Azerbaijani: its special letters or common function words."""
    if len(_AR.findall(text)) > len(_LAT.findall(text)):
        return "ar"
    if len(_AZ_LETTERS.findall(text)) >= 1 or len(_AZ_WORDS.findall(text)) >= 2:
        return "az"
    return "en"


def normalize_arabic(s: str) -> str:
    s = _AR_MARKS.sub("", s)
    s = re.sub("[إأآٱا]", "ا", s)
    return s.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")


def normalize_for_match(s: str) -> str:
    # Azerbaijani/Turkish dotted capital I lowercases to "i" + combining dot in Python: fix it first
    s = s.replace("İ", "i")
    s = unicodedata.normalize("NFKC", s).translate(_DIGITS).replace("\u0307", "")
    s = normalize_arabic(s)
    s = _QUOTES.sub("", s)
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return _WS.sub(" ", s).strip().lower()


def tokenize(s: str) -> list[str]:
    toks = re.findall(r"\w+", normalize_for_match(s))
    stop = _EN_STOP | {normalize_arabic(w) for w in _AR_STOP} | _AZ_STOP
    return [t for t in toks if (len(t) > 1 or t.isdigit()) and t not in stop]


_AR_PREFIX = re.compile(r"^(وال|بال|كال|فال|لل|ال|و|ب|ل|ف)(?=\w{3,})")


def match_terms(s: str) -> list[str]:
    """Tokens for the offline matcher: tokenize() plus light stemming so inflected
    forms meet (Arabic article/preposition prefixes; a 5-letter prefix for EN/AZ words)."""
    out: list[str] = []
    for t in tokenize(s):
        if _AR.search(t):
            t = _AR_PREFIX.sub("", t)
            out.append(t)
            if len(t) >= 5:
                out.append("~" + t[:4])
        else:
            out.append(t)
            if len(t) >= 6:
                out.append("~" + t[:5])
    return out


def to_ascii_digits(s: str) -> str:
    return s.translate(_DIGITS)
