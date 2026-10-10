"""Buyers are matched automatically by net price (price − transport per km), and re-matched when a
buyer joins or changes demand/price, and once more at pickup (matching.rematch_*)."""

from __future__ import annotations

from datetime import date

import pytest

from clearsky.config import reset_settings
from clearsky.domain import matching
from clearsky.domain.matching import Booked, book_pickup
from clearsky.models import BookingStatus
from clearsky.repo import BookingsRepo, BuyersRepo
from tests import factories as fx
from tests.apiclient import OFFICER, call
from tests.factories import BASE_LAT

TODAY = date(2026, 10, 20)
PHONE = "+919900000001"


@pytest.fixture
def world(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """One field; BY1 pays ₹1,900/t about 11 km away (≈ ₹1,811/t after transport)."""
    monkeypatch.setenv("DEV_AUTH", "true")
    reset_settings()
    fx.village("V1", "Testpur")
    fx.farmer(PHONE, name="Gurpreet")
    fx.baler("B1")
    fx.buyer("BY1", price=1900)
    fx.field("F1")


def booked() -> Booked:
    r = book_pickup("F1", TODAY)
    assert isinstance(r, Booked) and r.buyer_id == "BY1", r
    return r


def tonnes(buyer_id: str) -> tuple[float, float]:
    b = BuyersRepo().get(buyer_id)
    assert b is not None
    return b.reserved_tonnes, b.received_tonnes


def test_a_better_new_buyer_takes_open_straw(world: None) -> None:
    r = booked()
    payout = BookingsRepo().get(r.booking_id).farmer_payout  # type: ignore[union-attr]
    fx.buyer("BY2", price=1850, lat=BASE_LAT)  # at the field: ₹1,850/t net beats ₹1,811/t
    assert matching.rematch_open_bookings() == 1
    assert tonnes("BY1") == (0, 0) and tonnes("BY2") == (r.est_tonnes, 0)
    bk = BookingsRepo().get(r.booking_id)
    assert bk is not None
    assert (bk.buyer_id, bk.previous_buyer_id, bk.buyer_price_per_tonne) == ("BY2", "BY1", 1850)
    assert bk.buyer_changed_at is not None and bk.status == BookingStatus.OFFERED
    assert bk.farmer_payout == payout  # the farmer keeps the price they were promised
    assert matching.rematch_open_bookings() == 0  # stable: nothing better now


def test_a_closer_buyer_that_pays_less_after_transport_does_not_win(world: None) -> None:
    r = booked()
    fx.buyer("BY2", price=1700, lat=BASE_LAT)  # 0 km but ₹1,700/t < ₹1,811/t
    assert matching.rematch_open_bookings() == 0
    assert BookingsRepo().get(r.booking_id).buyer_id == "BY1"  # type: ignore[union-attr]


def test_radius_and_room_are_respected(world: None) -> None:
    r = booked()
    fx.buyer("BY2", price=5000, lat=BASE_LAT + 1.0, radius=20)  # pays a lot but ~111 km away
    fx.buyer("BY3", price=5000, lat=BASE_LAT, demand=5)  # pays a lot but has no room for 20 t
    assert matching.rematch_open_bookings() == 0
    assert BookingsRepo().get(r.booking_id).buyer_id == "BY1"  # type: ignore[union-attr]


def test_pickup_delivers_to_the_best_buyer_at_that_moment(world: None) -> None:
    r = booked()
    assert matching.accept_offer(r.booking_id).ok
    fx.buyer("BY2", price=1850, lat=BASE_LAT)  # joined after the booking, nobody re-ran anything
    assert matching.mark_done(r.booking_id).ok
    t = r.est_tonnes
    assert tonnes("BY1") == (0, 0) and tonnes("BY2") == (t, t)
    bk = BookingsRepo().get(r.booking_id)
    assert bk is not None and bk.status == BookingStatus.DONE and bk.buyer_id == "BY2"


def test_delivered_straw_is_never_moved(world: None) -> None:
    r = booked()
    assert matching.accept_offer(r.booking_id).ok and matching.mark_done(r.booking_id).ok
    fx.buyer("BY2", price=3000, lat=BASE_LAT)
    assert matching.rematch_open_bookings() == 0
    assert tonnes("BY1") == (r.est_tonnes, r.est_tonnes) and tonnes("BY2") == (0, 0)


def test_approving_a_buyer_rematches_open_bookings(world: None) -> None:
    r = booked()
    form = {
        "role": "buyer",
        "name": "Ravi Mehta",
        "phone": "+919812300002",
        "org_name": "Mehta Biofuels",
        "village_id": "V1",
        "type": "pellet",
        "price_per_tonne": 1850,
        "demand_tonnes": 500,
        "max_radius_km": 40,
    }
    status, out = call("POST", "/api/register", form, token="dev.pending.ravi")
    assert status == 200, out
    status, out = call(
        "POST", f"/api/applications/{out['application']['application_id']}/approve", token=OFFICER
    )
    assert status == 200 and out["rematched"] == 1, out
    new_id = out["entity"]["buyer_id"]
    assert BookingsRepo().get(r.booking_id).buyer_id == new_id  # type: ignore[union-attr]
    assert matching.accept_offer(r.booking_id).ok  # supply lists firm pickups, not open offers
    supply = call("GET", "/api/buyers/me/supply", token=f"dev.buyer.{new_id}")[1]
    assert [d["booking_id"] for d in supply["deliveries"]] == [r.booking_id]


def test_raising_the_price_wins_open_straw(world: None) -> None:
    r = booked()
    fx.buyer("BY2", price=1700, lat=BASE_LAT)
    assert matching.rematch_open_bookings() == 0
    demand = {"demand_tonnes": 1000, "price_per_tonne": 1850, "max_radius_km": 60}
    status, out = call("PUT", "/api/buyers/me/demand", demand, token="dev.buyer.BY2")
    assert status == 200 and out["rematched"] == 1
    assert out["buyer"]["reserved_tonnes"] == r.est_tonnes
    assert BookingsRepo().get(r.booking_id).buyer_id == "BY2"  # type: ignore[union-attr]
