"""Phase 1: models ⇄ DynamoDB, repositories and GSIs, transactions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from clearsky.models import Booking, BookingStatus, ConversationTurn, FieldStatus, to_item
from clearsky.models.dynamo import from_dynamo, to_dynamo
from clearsky.repo import (
    BalerDaysRepo,
    BookingsRepo,
    ConversationsRepo,
    FarmersRepo,
    FieldsRepo,
    SettingsRepo,
    VillagesRepo,
)
from clearsky.repo.transactions import TransactionCancelled, TxBuilder
from tests import factories as fx
from tests.factories import NOW


def test_decimal_round_trip() -> None:
    item = to_dynamo({"a": 2.5, "b": [1.25, {"c": 3.0}], "n": None, "s": "x"})
    assert item == {"a": Decimal("2.5"), "b": [Decimal("1.25"), {"c": Decimal("3.0")}], "s": "x"}
    assert from_dynamo(item) == {"a": 2.5, "b": [1.25, {"c": 3}], "s": "x"}


def test_villages_repo(ddb: None) -> None:
    fx.village("V1", "Alpha")
    fx.village("V2", "Beta")
    repo = VillagesRepo()
    assert repo.get("V1").name == "Alpha"  # type: ignore[union-attr]
    assert {v.village_id for v in repo.by_district("Sangrur")} == {"V1", "V2"}
    repo.update_fields("V1", {"fire_history_score": 0.75, "fire_points": 4})
    v1 = repo.get("V1")
    assert v1 is not None and v1.fire_history_score == 0.75 and v1.fire_points == 4
    assert repo.get("nope") is None


def test_farmers_and_fields_gsis(ddb: None) -> None:
    fx.village()
    fx.farmer("+919900000001")
    fx.farmer("+919900000002")
    fx.field("F1", phone="+919900000001", harvest=date(2026, 10, 22))
    fx.field("F2", phone="+919900000001", harvest=date(2026, 10, 30), status=FieldStatus.HARVESTED)
    fx.field("F3", phone="+919900000002", harvest=date(2026, 11, 2))

    assert len(FarmersRepo().by_village("V1")) == 2
    fields = FieldsRepo()
    assert [f.field_id for f in fields.by_farmer("+919900000001")] == ["F1", "F2"]
    assert {f.field_id for f in fields.by_village("V1", date(2026, 10, 21), date(2026, 10, 31))} == {
        "F1",
        "F2",
    }
    assert [f.field_id for f in fields.by_status(FieldStatus.HARVESTED)] == ["F2"]

    updated = fields.update("F1", {"status": FieldStatus.BOOKED, "booking_id": "BK-1"})
    assert updated.status == FieldStatus.BOOKED and updated.booking_id == "BK-1"
    removed = fields.update("F1", {"status": FieldStatus.HARVESTED}, remove=["booking_id"])
    assert removed.booking_id is None


def test_bookings_gsis_and_balerdays(ddb: None) -> None:
    repo = BookingsRepo()
    for i, (baler, d, status) in enumerate(
        [
            ("B1", date(2026, 10, 25), BookingStatus.CONFIRMED),
            ("B1", date(2026, 10, 25), BookingStatus.CANCELLED),
            ("B1", date(2026, 10, 26), BookingStatus.CONFIRMED),
            ("B2", date(2026, 10, 25), BookingStatus.CONFIRMED),
        ]
    ):
        repo.put(
            Booking(
                booking_id=f"BK{i}",
                field_id=f"F{i}",
                phone="+919900000001",
                village_id="V1",
                baler_id=baler,
                buyer_id="BY1",
                date=d,
                acres=5,
                est_tonnes=12.5,
                lat=30.0,
                lng=76.0,
                status=status,
                created_at=NOW,
            )
        )
    assert len(repo.by_baler("B1", date(2026, 10, 25))) == 2
    assert len(repo.confirmed_by_baler("B1", date(2026, 10, 25), date(2026, 10, 26))) == 2
    assert [b.booking_id for b in repo.by_field("F3")] == ["BK3"]
    assert len(repo.by_date(date(2026, 10, 25))) == 3
    repo.set_stop_order("BK0", 2)
    assert repo.get("BK0").stop_order == 2  # type: ignore[union-attr]
    assert BalerDaysRepo().range("B1", date(2026, 10, 1), date(2026, 10, 31)) == {}


def test_conversations_last_n_in_order(ddb: None) -> None:
    repo = ConversationsRepo()
    for i in range(5):
        repo.add(
            ConversationTurn(phone="+919900000001", ts=f"2026-10-20T10:00:0{i}", role="user", text=str(i))
        )
    turns = repo.last("+919900000001", 3)
    assert [t.text for t in turns] == ["2", "3", "4"]
    assert all(t.ttl for t in turns)


def test_settings_repo_clock(ddb: None) -> None:
    repo = SettingsRepo()
    assert repo.get_clock() is None
    repo.set_clock(date(2026, 10, 24))
    assert repo.get_clock() == date(2026, 10, 24)
    repo.set_clock(None)
    assert repo.get_clock() is None


def test_transaction_condition_failure_reports_index(ddb: None) -> None:
    fx.village()
    fx.field("F1")
    tx = TxBuilder()
    tx.put("Settings", {"key": "x", "v": 1.5})
    tx.update(
        "Fields",
        {"field_id": "F1"},
        "SET #s = :b",
        values={":b": "BOOKED", ":c": "CLEARED"},
        names={"#s": "status"},
        condition="#s = :c",
    )
    with pytest.raises(TransactionCancelled) as e:
        tx.execute()
    assert e.value.failed_index() == 1
    assert SettingsRepo().t.get_item(Key={"key": "x"}).get("Item") is None  # all-or-nothing


def test_to_item_drops_none() -> None:
    b = Booking(
        booking_id="BK",
        field_id="F",
        phone="+91",
        village_id="V",
        baler_id="B",
        date=date(2026, 10, 25),
        acres=1.5,
        est_tonnes=3.75,
        lat=1.0,
        lng=2.0,
        created_at=NOW,
    )
    item = to_item(b)
    assert "buyer_id" not in item and item["acres"] == Decimal("1.5") and item["date"] == "2026-10-25"
