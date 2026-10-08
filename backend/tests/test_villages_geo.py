"""Phase 1: geo helpers and fuzzy village resolution."""

from __future__ import annotations

import random

import pytest

from clearsky.domain.geo import bbox_contains, haversine_km, jitter_point, offset_point
from clearsky.domain.villages import fold, resolve
from clearsky.seed.generate import build_villages

VILLAGES = build_villages()


def test_haversine_known_distance() -> None:
    # One degree of latitude ≈ 111.2 km
    assert haversine_km(30.0, 76.0, 31.0, 76.0) == pytest.approx(111.2, abs=0.3)
    assert haversine_km(30.0, 76.0, 30.0, 76.0) == 0


def test_offset_and_jitter() -> None:
    lat, lng = offset_point(30.0, 76.0, 3, 4)
    assert haversine_km(30.0, 76.0, lat, lng) == pytest.approx(5.0, abs=0.05)
    rng = random.Random(1)
    for _ in range(200):
        p = jitter_point(30.0, 76.0, 1.5, rng)
        assert haversine_km(30.0, 76.0, *p) <= 1.51


def test_bbox_contains() -> None:
    bbox = (75.5, 29.7, 76.4, 30.5)
    assert bbox_contains(bbox, 30.25, 76.0)
    assert not bbox_contains(bbox, 31.0, 76.0)


@pytest.mark.parametrize(
    "query",
    ["Bhawanigarh", "bhavanigarh", "BHAWANIGADH", "भवानीगढ़", "ਭਵਾਨੀਗੜ੍ਹ", "bhawanigarh pind", "Bhawani garh"],
)
def test_resolve_bhawanigarh_spellings(query: str) -> None:
    matches = resolve(query, VILLAGES)
    assert matches, query
    assert matches[0].village_id == "V002", (query, matches)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("sangroor", "V001"),
        ("Sunaam", "V003"),
        ("lehra gaga", "V006"),
        ("Ghanauri", "V028"),
        ("बालियां", "V017"),
        ("ਛਾਜਲੀ", "V025"),
    ],
)
def test_resolve_other_villages(query: str, expected: str) -> None:
    assert resolve(query, VILLAGES)[0].village_id == expected


def test_resolve_unknown_and_empty() -> None:
    assert resolve("Mumbai", VILLAGES) == []
    assert resolve("", VILLAGES) == []
    assert resolve("village", VILLAGES) == []


def test_resolve_returns_at_most_three_sorted() -> None:
    matches = resolve("kalan", VILLAGES)
    assert len(matches) <= 3
    assert [m.score for m in matches] == sorted((m.score for m in matches), reverse=True)


def test_fold_spelling_variants() -> None:
    assert fold("Bhawanigarh") == fold("bhavanigarh")
    assert fold("Sunaam") == fold("sunam")
