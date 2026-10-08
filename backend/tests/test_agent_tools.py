"""Phase 3: tool validation and phone isolation (tools called directly)."""

from __future__ import annotations

from datetime import date

import pytest

from clearsky.agent import tools
from clearsky.agent.agent import TurnContext, build_tools
from clearsky.models import FieldStatus
from clearsky.repo import FieldsRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load

A = "+919900000001"
B = "+919900000002"


@pytest.fixture
def seeded(ddb: None) -> None:
    load(generate(42), prebook=False)


def _new_field(phone: str = A, acres: float = 8, harvest: str = "2026-10-24") -> dict[str, object]:
    assert tools.register_farmer(phone, "Gurpreet", "V002")["ok"]
    res = tools.register_field(phone, acres, harvest, "V002")
    assert res["ok"], res
    return res


@pytest.mark.parametrize(
    ("acres", "code"), [(0, "bad_acres"), (0.4, "bad_acres"), (101, "bad_acres"), ("lots", "bad_acres")]
)
def test_register_field_rejects_bad_acres(seeded: None, acres: object, code: str) -> None:
    tools.register_farmer(A, "Gurpreet", "V002")
    assert tools.register_field(A, acres, "2026-10-24", "V002")["error"] == code  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("harvest", "code"),
    [
        ("2026-09-01", "harvest_date_too_old"),  # before season start
        ("2026-10-01", "harvest_date_too_old"),  # more than 15 days before today (Oct 20)
        ("2026-11-14", "harvest_date_out_of_season"),  # too close to the Nov 15 cutoff
        ("24 Oct", "bad_date"),
    ],
)
def test_register_field_rejects_bad_dates(seeded: None, harvest: str, code: str) -> None:
    tools.register_farmer(A, "Gurpreet", "V002")
    assert tools.register_field(A, 8, harvest, "V002")["error"] == code


def test_register_field_rejects_unknown_village_and_unregistered_farmer(seeded: None) -> None:
    assert tools.register_field(A, 8, "2026-10-24", "V002")["error"] == "farmer_not_registered"
    tools.register_farmer(A, "Gurpreet", "V002")
    assert tools.register_field(A, 8, "2026-10-24", "V999")["error"] == "unknown_village"
    assert tools.register_farmer(B, "X", "V999")["error"] == "unknown_village"
    assert tools.register_farmer(B, "  ", "V002")["error"] == "bad_name"


def test_register_field_sowing_date_rules(seeded: None) -> None:
    tools.register_farmer(A, "Gurpreet", "V002")
    assert tools.register_field(A, 8, "2026-10-24", "V002", "2026-10-20")["error"] == "bad_sowing_date"
    res = tools.register_field(A, 8, "2026-10-24", "V002", "2026-11-05")
    assert res["ok"] and res["sowing_deadline"] == "2026-11-05"


def test_register_field_past_harvest_is_harvested_and_idempotent(seeded: None) -> None:
    tools.register_farmer(A, "Gurpreet", "V002")
    first = tools.register_field(A, 6, "2026-10-17", "V002")
    assert first["status"] == "HARVESTED" and first["harvest_confirmed"] is True
    again = tools.register_field(A, 6, "2026-10-17", "V002")
    assert again["duplicate"] is True and again["field_id"] == first["field_id"]


def test_resolve_village_tool(seeded: None) -> None:
    assert tools.resolve_village("bhavanigarh")["matches"][0]["village_id"] == "V002"
    assert tools.resolve_village("Mumbai")["matches"] == []
    assert tools.resolve_village("  ")["error"] == "empty_name"


def test_full_booking_via_tools(seeded: None) -> None:
    field = _new_field()
    booked = tools.book_pickup(A, str(field["field_id"]))
    assert booked["ok"] and booked["pickup_date"] == "2026-10-25"
    profile = tools.get_my_profile(A)
    assert profile["registered"] and profile["village_name"] == "Bhawanigarh"
    assert profile["fields"][0]["status"] == "BOOKED"
    assert tools.get_my_bookings(A)["bookings"][0]["booking_id"] == booked["booking_id"]


def test_phone_isolation(seeded: None) -> None:
    field = _new_field(A)
    fid = str(field["field_id"])
    booked = tools.book_pickup(A, fid)
    tools.register_farmer(B, "Harjit", "V002")

    assert tools.book_pickup(B, fid)["error"] == "field_not_found"
    assert tools.confirm_harvest(B, fid)["error"] == "field_not_found"
    assert tools.reschedule(B, fid, "2026-10-28")["error"] == "field_not_found"
    assert tools.cancel_booking(B, str(booked["booking_id"]))["error"] == "booking_not_found"
    assert tools.get_my_profile(B)["fields"] == []
    assert tools.get_my_bookings(B)["bookings"] == []
    # A's data is untouched
    f = FieldsRepo().get(fid)
    assert f is not None and f.status == FieldStatus.BOOKED and f.harvest_date == date(2026, 10, 24)


def test_tool_specs_never_expose_phone() -> None:
    for t in build_tools(A, TurnContext()):
        props = t.tool_spec["inputSchema"]["json"].get("properties", {})
        assert "phone" not in props, t.tool_name


def test_confirm_reschedule_cancel(seeded: None) -> None:
    field = _new_field()
    fid = str(field["field_id"])
    confirmed = tools.confirm_harvest(A, fid)
    assert confirmed["harvest_confirmed"] and confirmed["status"] == "HARVESTED"
    booked = tools.book_pickup(A, fid)
    moved = tools.reschedule(A, fid, "2026-10-28")
    assert (
        moved["ok"] and moved["pickup_date"] == "2026-10-29" and moved["booking_id"] != booked["booking_id"]
    )
    assert tools.reschedule(A, fid, "2026-12-01")["error"] == "harvest_date_out_of_range"
    assert tools.cancel_booking(A, str(moved["booking_id"])) == {"ok": True}
    assert tools.cancel_booking(A, str(moved["booking_id"]))["error"] == "not_cancellable"
