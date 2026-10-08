"""Fuzzy village-name resolution over English, aliases, Hindi and Punjabi names."""

from __future__ import annotations

import re
import time
import unicodedata

from pydantic import BaseModel
from rapidfuzz import fuzz

from clearsky.models import Village

MIN_SCORE = 70.0
_STOPWORDS = {
    "village",
    "pind",
    "gaon",
    "gaav",
    "gav",
    "gram",
    "vill",
    "vpo",
    "po",
    "teh",
    "tehsil",
    "district",
    "zila",
    "jila",
    "पिंड",
    "गांव",
    "गाँव",
    "ग्राम",
    "ਪਿੰਡ",
    "ਗਰਾਮ",
}
# Spelling variants that are common when Punjabi/Hindi names are typed in Roman script.
_FOLDS = [
    ("w", "v"),
    ("aa", "a"),
    ("ee", "i"),
    ("oo", "u"),
    ("ou", "u"),
    ("sh", "s"),
    ("kh", "k"),
    ("gh", "g"),
    ("dh", "d"),
    ("bh", "b"),
    ("th", "t"),
    ("ph", "f"),
    ("z", "j"),
    ("y", "i"),
]

_cache: tuple[float, list[Village]] | None = None
_CACHE_SECONDS = 300.0


class VillageMatch(BaseModel):
    village_id: str
    name: str
    block: str
    score: float


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFC", text).casefold()
    t = re.sub(r"[^\w\s]", " ", t)
    words = [w for w in t.split() if w not in _STOPWORDS]
    return " ".join(words)


def fold(text: str) -> str:
    t = normalise(text)
    if t.isascii():
        for a, b in _FOLDS:
            t = t.replace(a, b)
        t = re.sub(r"(.)\1+", r"\1", t)  # collapse doubled letters
    return t


def _candidates(v: Village) -> list[str]:
    return [s for s in [v.name, v.name_hi, v.name_pa, *v.aliases] if s]


def resolve(name: str, villages: list[Village] | None = None, limit: int = 3) -> list[VillageMatch]:
    """Top matches (score 0–100), best first. Empty list if nothing scores ≥ MIN_SCORE."""
    query = fold(name)
    if not query:
        return []
    pool = villages if villages is not None else _all_villages()
    scored: list[VillageMatch] = []
    for v in pool:
        best = 0.0
        for c in _candidates(v):
            fc = fold(c)
            if not fc:
                continue
            s = 100.0 if fc == query else max(fuzz.ratio(query, fc), fuzz.WRatio(query, fc) * 0.95)
            best = max(best, s)
        if best >= MIN_SCORE:
            scored.append(
                VillageMatch(village_id=v.village_id, name=v.name, block=v.block, score=round(best, 1))
            )
    scored.sort(key=lambda m: m.score, reverse=True)
    return scored[:limit]


def _all_villages() -> list[Village]:
    global _cache
    now = time.monotonic()
    if _cache is not None and now - _cache[0] < _CACHE_SECONDS:
        return _cache[1]
    from clearsky.repo import VillagesRepo

    villages = VillagesRepo().list_all()
    _cache = (now, villages)
    return villages


def clear_cache() -> None:
    global _cache
    _cache = None
