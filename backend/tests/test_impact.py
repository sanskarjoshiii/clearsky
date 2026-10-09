"""Issue #5: pollution avoided per cleared field and on the public impact page.

The factors below are TEST VALUES chosen to make the arithmetic obvious. They are not real emission
factors: clearsky ships with none, and the team must configure published, cited values.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from clearsky.config import reset_settings
from clearsky.domain import impact, matching, offers
from clearsky.models import BookingStatus
from clearsky.repo import BookingsRepo, ConversationsRepo
from tests import factories as fx
from tests.apiclient import OFFICER, call, operator

TODAY = date(2026, 10, 20)
PHONE = "+919900000001"
TEST_FACTORS = {
    "pm25": {
        "kg_per_tonne": 2.0,
        "source": "TEST VALUE, not a real emission factor",
        "url": "https://example.test/pm25",
    },
    "co2": {"kg_per_tonne": 1000.0, "source": "TEST VALUE, not a real emission factor"},
    "co": {"kg_per_tonne": 50.0},  # no source → must be ignored
    "nox": {"kg_per_tonne": 3.0, "source": "TEST VALUE"},  # not a pollutant clearsky reports → ignored
}


def configure(
    monkeypatch: pytest.MonkeyPatch, factors: dict[str, Any] | None, burn_fraction: float | None = None
) -> None:
    if factors is None:
        monkeypatch.delenv("EMISSION_FACTORS", raising=False)
    else:
        monkeypatch.setenv("EMISSION_FACTORS", json.dumps(factors))
    if burn_fraction is not None:
        monkeypatch.setenv("BURN_FRACTION", str(burn_fraction))
    reset_settings()


@pytest.fixture
def world(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two farmers in two villages, one baler, one buyer; pickups are confirmed at once."""
    monkeypatch.setenv("DEV_AUTH", "true")
    monkeypatch.setenv("AUTO_ACCEPT_DEMO", "true")
    configure(monkeypatch, TEST_FACTORS)
    fx.village("V1", "Testpur")
    fx.village("V2", "Otherpur")
    fx.farmer(PHONE, name="Gurpreet Singh")
    fx.farmer("+919900000002", village_id="V2", name="Harjit")
    fx.baler("B1", acres_per_day=40)
    fx.buyer("BY1")
    fx.field("F1", acres=8)  # 20 t of straw
    fx.field("F2", phone="+919900000002", village_id="V2", acres=4)  # 10 t


def book(field_id: str) -> str:
    r = matching.book_pickup(field_id, TODAY)
    assert isinstance(r, matching.Booked)
    return r.booking_id


def done(field_id: str) -> Any:
    booking_id = book(field_id)
    status, body = call("POST", f"/api/bookings/{booking_id}/done", token=operator("B1"))
    assert status == 200
    return body


# ------------------------------------------------------------------ calculation


def test_only_sourced_known_factors_count(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, None)
    assert impact.factors() == {} and impact.compute(20) == {} and impact.snapshot(20) == {}
    assert impact.version() is None and impact.describe()["configured"] is False

    configure(monkeypatch, TEST_FACTORS)
    assert list(impact.factors()) == ["pm25", "co2"]  # display order; unsourced CO and unknown NOx dropped
    assert impact.compute(20) == {"pm25": 40.0, "co2": 20000.0}  # tonnes × kg per tonne
    meta = impact.describe()
    assert meta["estimate"] is True and meta["burn_fraction"] == 1.0
    assert meta["factors"]["pm25"] == {
        "label": "PM2.5",
        "unit": "kg",
        "kg_per_tonne": 2.0,
        "source": "TEST VALUE, not a real emission factor",
        "url": "https://example.test/pm25",
    }
    assert meta["factors"]["co2"]["unit"] == "t"
    assert impact.in_unit("co2", 20000.0) == 20.0 and impact.in_unit("pm25", 40.0) == 40.0


def test_burn_fraction_scales_and_changes_the_version(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, TEST_FACTORS)
    full = impact.version()
    configure(monkeypatch, TEST_FACTORS, burn_fraction=0.5)
    assert impact.compute(20) == {"pm25": 20.0, "co2": 10000.0}
    assert impact.version() != full and impact.describe()["burn_fraction"] == 0.5


def test_bad_factor_values_are_ignored(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    configure(
        monkeypatch,
        {
            "pm25": {"kg_per_tonne": "abc", "source": "x"},
            "pm10": {"kg_per_tonne": -1, "source": "x"},
            "bc": "nope",
        },
    )
    assert impact.factors() == {}


def test_public_names_are_masked() -> None:
    assert impact.mask_name("Gurpreet Singh") == "Gurpreet S."
    assert impact.mask_name("Harjit") == "Harjit"
    assert impact.mask_name("Bhai Gurdeep Singh Grewal") == "Bhai G."
    assert impact.mask_name("") is None and impact.mask_name(None) is None


# ------------------------------------------------------------------ snapshot on done


def test_done_stores_a_snapshot_and_tells_everyone(world: None) -> None:
    body = done("F1")
    snap = body["booking"]
    assert snap["impact"] == {"pm25": 40.0, "co2": 20000.0} and snap["impact_tonnes"] == 20
    assert snap["impact_factors_version"] == impact.version()
    assert body["impact"]["pm25"] == {
        "kg": 40.0,
        "value": 40.0,
        "unit": "kg",
        "label": "PM2.5",
        "source": "TEST VALUE, not a real emission factor",
        "url": "https://example.test/pm25",
    }
    assert body["impact"]["co2"]["value"] == 20.0 and body["impact"]["co2"]["unit"] == "t"
    stored = BookingsRepo().get(snap["booking_id"])
    assert stored is not None and stored.impact == {"pm25": 40.0, "co2": 20000.0}
    # the farmer's "field cleared" message carries the PM2.5 estimate
    message = ConversationsRepo().last(PHONE, 1)[0].text
    assert message.startswith("✅ Gurpreet Singh ji, aapka khet aaj saaf ho gaya.")
    assert "lagbhag 40 kg dhuan (PM2.5) rukne ka anumaan" in message


def test_without_factors_nothing_is_stored_or_shown(world: None, monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, None)
    body = done("F1")
    assert body["booking"].get("impact") is None and body["impact"] == {}
    stats = call("GET", "/api/stats")[1]
    assert stats["impact"] == {} and stats["impact_configured"] is False and "pm25_avoided_kg" not in stats
    assert ConversationsRepo().last(PHONE, 1)[0].text == (
        "✅ Gurpreet Singh ji, aapka khet aaj saaf ho gaya. Parali na jalane ke liye dhanyavaad! 🙏"
    )
    table = call("GET", "/api/impact")[1]
    assert table["configured"] is False and table["district"]["impact"] == {}
    assert table["district"]["fields"] == 1  # acres and tonnes are still reported


def test_history_does_not_change_when_factors_are_edited(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = done("F1")["booking"]
    doubled = {k: v | {"kg_per_tonne": v["kg_per_tonne"] * 2} for k, v in TEST_FACTORS.items()}
    configure(monkeypatch, doubled)
    second = done("F2")["booking"]
    assert BookingsRepo().get(first["booking_id"]).impact == {"pm25": 40.0, "co2": 20000.0}  # type: ignore[union-attr]
    assert second["impact"] == {"pm25": 40.0, "co2": 20000.0}  # 10 t at the doubled factors
    assert second["impact_factors_version"] != first["impact_factors_version"]
    # a pollutant whose factor was withdrawn is no longer shown, though the snapshot keeps it
    configure(monkeypatch, {"pm25": TEST_FACTORS["pm25"]})
    assert call("GET", "/api/stats")[1]["impact"].keys() == {"pm25"}
    assert BookingsRepo().get(first["booking_id"]).impact["co2"] == 20000.0  # type: ignore[union-attr, index]


def test_cancelled_declined_and_open_bookings_never_count(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    cancelled = book("F1")
    assert matching.cancel_booking(cancelled, TODAY)
    monkeypatch.setenv("AUTO_ACCEPT_DEMO", "false")
    reset_settings()
    offered = book("F2")
    offers.decline(offered, "B1", "too_far")
    statuses = {b.status for b in BookingsRepo().list_all()}
    assert statuses == {BookingStatus.CANCELLED, BookingStatus.DECLINED}
    assert all(b.impact is None for b in BookingsRepo().list_all())
    assert call("GET", "/api/stats")[1]["impact"] == {}
    table = call("GET", "/api/impact")[1]
    assert table["groups"] == [] and table["district"]["fields"] == 0


# ------------------------------------------------------------------ aggregation and surfaces


def test_stats_and_role_views_aggregate_snapshots(world: None) -> None:
    done("F1")
    done("F2")
    stats = call("GET", "/api/stats")[1]
    assert stats["impact_estimate"] is True and stats["impact_configured"] is True
    assert stats["impact"]["pm25"]["kg"] == 60.0 and stats["impact"]["co2"]["value"] == 30.0
    assert stats["impact_factors"]["pm25"]["source"] == "TEST VALUE, not a real emission factor"

    window = {"from": "2026-10-01", "to": "2026-10-31"}  # the pickups were marked done ahead of their day
    history = call("GET", "/api/operator/me/history", token=operator("B1"), query=window)[1]
    assert history["totals"]["impact"]["pm25"]["kg"] == 60.0
    assert {r["impact"]["pm25"] for r in history["rows"]} == {40.0, 20.0}
    day = BookingsRepo().list_all()[0].date.isoformat()
    route = call("GET", "/api/operator/me/route", token=operator("B1"), query={"date": day})[1]
    assert {s["impact"]["pm25"] for s in route["stops"]} == {40.0, 20.0}

    supply = call("GET", "/api/buyers/me/supply", token="dev.buyer.BY1")[1]
    assert supply["impact"]["pm25"]["kg"] == 60.0
    assert {d["impact"]["pm25"] for d in supply["deliveries"]} == {40.0, 20.0}

    detail = call("GET", "/api/fields/F1", token=OFFICER)[1]
    assert detail["bookings"][0]["impact"] == {"pm25": 40.0, "co2": 20000.0}
    rows = call("GET", "/api/bookings", token=OFFICER)[1]["bookings"]
    assert sorted(r["impact"]["pm25"] for r in rows) == [20.0, 40.0]


def test_public_table_groups_by_village_without_personal_data(world: None) -> None:
    done("F1")
    done("F2")
    status, table = call("GET", "/api/impact")  # public: no token
    assert status == 200 and table["estimate"] is True and table["primary"] == "pm25"
    assert table["district"]["label"] == "Sangrur district"
    assert (table["district"]["fields"], table["district"]["acres"], table["district"]["tonnes"]) == (
        2,
        12,
        30,
    )
    assert table["district"]["impact"] == {"pm25": 60.0, "co2": 30000.0}
    assert (
        table["district"]["trend"][0]["cumulative"] == 0
        and table["district"]["trend"][-1]["cumulative"] == 60.0
    )
    assert [g["label"] for g in table["groups"]] == ["Testpur", "Otherpur"]  # most straw first
    testpur = table["groups"][0]
    assert testpur["impact"] == {"pm25": 40.0, "co2": 20000.0} and testpur["fields"] == 1
    row = testpur["rows"][0]
    assert row["label"] == "Gurpreet S." and row["village"] == "Testpur" and row["acres"] == 8
    assert row["impact"]["pm25"] == 40.0 and row["trend"][-1]["cumulative"] == 40.0
    blob = json.dumps(table)
    assert "+91" not in blob and "9900000001" not in blob and "Gurpreet Singh" not in blob
    assert "booking_id" not in blob and "field_id" not in blob and "phone" not in blob

    flat = call("GET", "/api/impact", query={"group": "field"})[1]
    assert {r["label"] for r in flat["rows"]} == {"Gurpreet S.", "Harjit"} and "groups" not in flat
    weekly = call("GET", "/api/impact", query={"period": "week"})[1]
    week = weekly["weeks"][0]
    assert weekly["district"]["by_week"][week] == {"pm25": 60.0, "co2": 30000.0}
    assert weekly["groups"][0]["rows"][0]["by_week"][week]["pm25"] == 40.0
    assert call("GET", "/api/impact", query={"group": "phone"})[0] == 400


# ------------------------------------------------------------------ backfill


def test_backfill_fills_old_bookings_and_only_recomputes_on_request(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.backfill_impact import backfill

    configure(monkeypatch, None)
    old = done("F1")["booking"]["booking_id"]  # done before any factor was configured
    with pytest.raises(SystemExit):
        backfill()
    configure(monkeypatch, TEST_FACTORS)
    assert backfill(dry_run=True) == {"done": 1, "written": 1, "current": 0, "kept": 0}
    assert BookingsRepo().get(old).impact is None  # type: ignore[union-attr]
    assert backfill() == {"done": 1, "written": 1, "current": 0, "kept": 0}
    assert BookingsRepo().get(old).impact == {"pm25": 40.0, "co2": 20000.0}  # type: ignore[union-attr]
    assert backfill() == {"done": 1, "written": 0, "current": 1, "kept": 0}

    # the team changes a factor: history stays until someone asks for a recompute
    configure(monkeypatch, {"pm25": TEST_FACTORS["pm25"] | {"kg_per_tonne": 3.0}})
    assert backfill() == {"done": 1, "written": 0, "current": 0, "kept": 1}
    assert BookingsRepo().get(old).impact["pm25"] == 40.0  # type: ignore[union-attr, index]
    assert backfill(recompute=True) == {"done": 1, "written": 1, "current": 0, "kept": 0}
    assert BookingsRepo().get(old).impact == {"pm25": 60.0}  # type: ignore[union-attr]
