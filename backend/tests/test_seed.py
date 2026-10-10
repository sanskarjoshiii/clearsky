"""Phase 1: deterministic seed generation and loading."""

from __future__ import annotations

from pathlib import Path

from clearsky.models import FieldStatus
from clearsky.repo import BookingsRepo, BuyersRepo, FieldsRepo, VillagesRepo
from clearsky.seed.generate import generate, read, write
from clearsky.seed.load import load, reset_all


def test_generate_is_deterministic(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    write(generate(42), a)
    write(generate(42), b)
    for p in a.iterdir():
        assert p.read_bytes() == (b / p.name).read_bytes(), p.name
    assert generate(42) != generate(7)


def test_seed_content_rules() -> None:
    data = generate(42)
    assert 28 <= len(data["villages"]) <= 32
    assert all(v["approx"] for v in data["villages"])
    assert len(data["balers"]) == 10
    assert all(12 <= b["acres_per_day"] <= 20 and 15 <= b["radius_km"] <= 25 for b in data["balers"])
    assert all("operator_phone" not in b for b in data["balers"])
    assert len(data["buyers"]) == 3 and all(b["name"].startswith("Demo ") for b in data["buyers"])
    assert 50 <= len(data["fields"]) <= 80
    assert all(f["synthetic"] for f in data["farmers"])
    assert all(2 <= f["acres"] <= 15 for f in data["fields"])
    assert len(data["meta"]["red_candidate_field_ids"]) == 10
    red = {
        f["field_id"]: f for f in data["fields"] if f["field_id"] in data["meta"]["red_candidate_field_ids"]
    }
    assert all(f["status"] == "HARVESTED" for f in red.values())
    assert not set(red) & set(data["meta"]["prebook_field_ids"])


def test_write_then_read_round_trip(tmp_path: Path) -> None:
    write(generate(42), tmp_path)
    data = read(tmp_path)
    assert data["meta"]["seed"] == 42 and len(data["villages"]) == len(generate(42)["villages"])


def test_load_into_tables_with_prebooking(ddb: None) -> None:
    data = generate(42)
    summary = load(data, reset=True)
    assert summary["villages"] == len(data["villages"])
    assert summary["prebooked"] >= 1
    assert len(VillagesRepo().list_all()) == len(data["villages"])
    booked = FieldsRepo().by_status(FieldStatus.BOOKED)
    assert len(booked) == summary["prebooked"]
    assert len(BookingsRepo().list_all()) == summary["prebooked"]
    assert sum(b.reserved_tonnes for b in BuyersRepo().list_all()) > 0
    # reload with reset leaves a clean, equal state
    reset_all()
    assert VillagesRepo().list_all() == []


def test_fire_history_is_kept_and_red_candidates_go_where_red_is_reachable() -> None:
    from datetime import date

    from clearsky.domain.risk import score_field
    from clearsky.models import Field, RiskLevel

    plain = generate(42)
    hot = {"V026": 1.0, "V025": 0.92, "V024": 0.80}  # like real FIRMS: only a few villages burn a lot
    fire = {
        v["village_id"]: {"fire_points": 10, "fire_history_score": hot.get(v["village_id"], 0.2)}
        for v in plain["villages"]
    }
    data = generate(42, fire=fire)
    assert {v["village_id"]: v["fire_history_score"] for v in data["villages"]}["V026"] == 1.0
    red_ids = set(data["meta"]["red_candidate_field_ids"])
    ref = date.fromisoformat(data["meta"]["reference_date"])
    for f in data["fields"]:
        if f["field_id"] in red_ids:
            assert f["village_id"] in hot
            r = score_field(Field.model_validate(f), hot[f["village_id"]], ref, slot_available=True)
            assert r.level == RiskLevel.RED, (f["field_id"], r.score)
    # same rng draws: every non-candidate field is unchanged
    others = lambda d: [f for f in d["fields"] if f["field_id"] not in red_ids]  # noqa: E731
    assert others(data) == others(plain)
