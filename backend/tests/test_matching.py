"""Phase 2: matching and booking engine."""

from __future__ import annotations

from datetime import date

import pytest

from clearsky.domain import matching
from clearsky.domain.matching import Booked, NoSlot, book_pickup, cancel_booking, reschedule
from clearsky.models import BookingStatus, FieldStatus
from clearsky.repo import BalerDaysRepo, BookingsRepo, BuyersRepo, FieldsRepo
from tests import factories as fx
from tests.factories import BASE_LAT, BASE_LNG, km_east

TODAY = date(2026, 10, 20)
D1 = date(2026, 10, 23)  # first bookable day for a field harvested on Oct 22


@pytest.fixture
def world(ddb: None) -> None:
    fx.village("V1", "Testpur")
    fx.village("V2", "Otherpur", lng=km_east(BASE_LNG, 4))
    fx.farmer()


def _booked(r: matching.BookingResult) -> Booked:
    assert isinstance(r, Booked), r
    return r


def test_picks_nearest_baler_when_all_else_equal(world: None) -> None:
    fx.baler("B_FAR", lng=km_east(BASE_LNG, 8))
    fx.baler("B_NEAR", lng=km_east(BASE_LNG, 2))
    fx.buyer()
    fx.field("F1")
    r = _booked(book_pickup("F1", TODAY))
    assert (r.baler_id, r.date, r.stop_order) == ("B_NEAR", D1, 1)
    f = FieldsRepo().get("F1")
    assert f is not None and f.status == FieldStatus.BOOKED and f.booking_id == r.booking_id
    day = BalerDaysRepo().get("B_NEAR", D1)
    assert day is not None and (day.booked_acres, day.stop_count, day.capacity_acres) == (8, 1, 15)


def test_respects_capacity_second_field_moves_to_next_day(world: None) -> None:
    fx.baler("B1", acres_per_day=15)
    fx.field("F1", acres=10)
    fx.field("F2", acres=10)
    assert _booked(book_pickup("F1", TODAY)).date == D1
    assert _booked(book_pickup("F2", TODAY)).date == date(2026, 10, 24)


def test_capacity_overflow_goes_to_other_baler_if_cheaper(world: None) -> None:
    fx.baler("B1", acres_per_day=15)
    fx.baler("B2", acres_per_day=15, lng=km_east(BASE_LNG, 1))  # 1 km < delay penalty 2
    fx.field("F1", acres=10)
    fx.field("F2", acres=10)
    first = _booked(book_pickup("F1", TODAY))
    second = _booked(book_pickup("F2", TODAY))
    assert first.baler_id == "B1" and (second.baler_id, second.date) == ("B2", D1)


def test_respects_deadline(world: None) -> None:
    fx.baler("B1")
    # deadline Oct 24 − buffer 2 = Oct 22 < first possible day Oct 23
    fx.field("F1", harvest=date(2026, 10, 22), deadline=date(2026, 10, 24))
    r = book_pickup("F1", TODAY)
    assert isinstance(r, NoSlot) and r.reason == "deadline_too_close"
    # never booked after sowing_deadline − buffer
    fx.field("F2", acres=10, harvest=date(2026, 10, 22), deadline=date(2026, 10, 26))  # window Oct 23–24
    fx.field("F3", acres=10, harvest=date(2026, 10, 22), deadline=date(2026, 10, 26))
    fx.field("F4", acres=10, harvest=date(2026, 10, 22), deadline=date(2026, 10, 26))
    assert _booked(book_pickup("F2", TODAY)).date == D1
    assert _booked(book_pickup("F3", TODAY)).date == date(2026, 10, 24)
    r4 = book_pickup("F4", TODAY)
    assert isinstance(r4, NoSlot) and r4.reason == "no_baler_capacity"


def test_cluster_bonus_prefers_baler_already_in_village(world: None) -> None:
    fx.baler("B_NEAR", lng=km_east(BASE_LNG, 3))
    fx.baler("B_CLUSTER", lng=km_east(BASE_LNG, 5), acres_per_day=20)
    fx.farmer("+919900000002")
    fx.field("F_EXISTING", phone="+919900000002", acres=4)
    # put the first field on B_CLUSTER directly by making B_NEAR temporarily unavailable
    fx.baler("B_NEAR", lng=km_east(BASE_LNG, 3), active=False)
    assert _booked(book_pickup("F_EXISTING", TODAY)).baler_id == "B_CLUSTER"
    fx.baler("B_NEAR", lng=km_east(BASE_LNG, 3), active=True)

    fx.field("F_NEW", acres=4)
    r = _booked(book_pickup("F_NEW", TODAY))
    assert (r.baler_id, r.date) == ("B_CLUSTER", D1)  # 5 − 5 (cluster) < 3


def test_ignores_inactive_and_out_of_radius_balers(world: None) -> None:
    fx.baler("B_OFF", active=False)
    fx.baler("B_FAR", lng=km_east(BASE_LNG, 30), radius_km=20)
    fx.field("F1")
    r = book_pickup("F1", TODAY)
    assert isinstance(r, NoSlot) and r.reason == "no_baler_capacity"


def test_buyer_choice_maximises_net_price(world: None) -> None:
    fx.baler("B1")
    lat30 = BASE_LAT + 30 / 110.574
    lat50 = BASE_LAT + 50 / 110.574
    fx.buyer("BY_NEAR", lat=lat30, price=1800, radius=80)  # net 1800 − 8·30 = 1560
    fx.buyer("BY_RICH", lat=lat50, price=1900, radius=80)  # net 1900 − 8·50 = 1500
    fx.buyer("BY_FULL", lat=BASE_LAT, price=5000, demand=100, reserved=95)  # not enough room
    fx.buyer("BY_OUT", lat=BASE_LAT, price=5000, radius=0.1, lng=km_east(BASE_LNG, 5))  # out of radius
    fx.field("F1", acres=8)
    r = _booked(book_pickup("F1", TODAY))
    assert r.buyer_id == "BY_NEAR" and r.est_tonnes == 20
    assert BuyersRepo().get("BY_NEAR").reserved_tonnes == 20  # type: ignore[union-attr]
    assert r.farmer_payout > 0 and not r.free_clearance


def test_books_without_buyer_as_free_clearance(world: None) -> None:
    fx.baler("B1")
    fx.field("F1")
    r = _booked(book_pickup("F1", TODAY))
    assert r.buyer_id is None and r.buyer_name is None and r.free_clearance and r.farmer_payout == 0


def test_concurrent_bookings_for_last_capacity_exactly_one_succeeds(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both requests read the ledger before either commits (stale read). The transaction must stop one."""
    fx.baler("B1", acres_per_day=15)
    fx.field("FA", acres=10, deadline=date(2026, 10, 25))  # window: Oct 23 only
    fx.field("FB", acres=10, deadline=date(2026, 10, 25))
    stale_a = matching._load_candidates(FieldsRepo().get("FA"), TODAY)  # type: ignore[arg-type]
    stale_b = matching._load_candidates(FieldsRepo().get("FB"), TODAY)  # type: ignore[arg-type]
    assert len(stale_a) == len(stale_b) == 1

    stale = {"FA": stale_a, "FB": stale_b}
    monkeypatch.setattr(matching, "_load_candidates", lambda field, today: stale[field.field_id])
    results = [book_pickup("FA", TODAY), book_pickup("FB", TODAY)]
    assert sum(isinstance(r, Booked) for r in results) == 1
    loser = next(r for r in results if isinstance(r, NoSlot))
    assert loser.reason == "contention"
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and day.booked_acres == 10
    assert FieldsRepo().get("FB").status == FieldStatus.REGISTERED  # type: ignore[union-attr]
    assert len(BookingsRepo().list_all()) == 1


def test_cancel_frees_capacity_and_buyer_reservation(world: None) -> None:
    fx.baler("B1")
    fx.buyer("BY1")
    fx.field("F1")
    r = _booked(book_pickup("F1", TODAY))
    assert cancel_booking(r.booking_id, TODAY)
    assert BookingsRepo().get(r.booking_id).status == BookingStatus.CANCELLED  # type: ignore[union-attr]
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and (day.booked_acres, day.stop_count) == (0, 0)
    assert BuyersRepo().get("BY1").reserved_tonnes == 0  # type: ignore[union-attr]
    f = FieldsRepo().get("F1")
    assert f is not None and f.status == FieldStatus.REGISTERED and f.booking_id is None
    assert not cancel_booking(r.booking_id, TODAY)  # second cancel is a no-op
    # the freed day can be booked again
    assert _booked(book_pickup("F1", TODAY)).date == D1


def test_cancel_after_harvest_returns_field_to_harvested(world: None) -> None:
    fx.baler("B1")
    fx.field("F1", harvest=date(2026, 10, 19))
    r = _booked(book_pickup("F1", TODAY))
    assert cancel_booking(r.booking_id, TODAY)
    assert FieldsRepo().get("F1").status == FieldStatus.HARVESTED  # type: ignore[union-attr]


def test_booking_a_booked_field_is_idempotent(world: None) -> None:
    fx.baler("B1")
    fx.field("F1")
    first = _booked(book_pickup("F1", TODAY))
    again = _booked(book_pickup("F1", TODAY))
    assert again.booking_id == first.booking_id and again.already_booked
    assert len(BookingsRepo().list_all()) == 1


def test_not_found_and_not_bookable(world: None) -> None:
    assert book_pickup("nope", TODAY) == NoSlot(field_id="nope", reason="not_found")
    fx.field("F1", status=FieldStatus.CLEARED)
    r = book_pickup("F1", TODAY)
    assert isinstance(r, NoSlot) and r.reason == "not_bookable"


def test_reschedule_moves_booking(world: None) -> None:
    fx.baler("B1")
    fx.field("F1")
    first = _booked(book_pickup("F1", TODAY))
    moved = _booked(reschedule("F1", date(2026, 10, 30), TODAY))
    assert moved.date == date(2026, 10, 31) and moved.booking_id != first.booking_id
    assert BookingsRepo().get(first.booking_id).status == BookingStatus.CANCELLED  # type: ignore[union-attr]
    f = FieldsRepo().get("F1")
    assert f is not None and f.harvest_date == date(2026, 10, 30) and f.sowing_deadline == date(2026, 11, 15)


def test_oversized_field_only_takes_an_empty_day(world: None) -> None:
    fx.baler("B1", acres_per_day=12)
    fx.field("F_SMALL", acres=3)
    fx.field("F_BIG", acres=14)
    assert _booked(book_pickup("F_SMALL", TODAY)).date == D1
    assert _booked(book_pickup("F_BIG", TODAY)).date == date(2026, 10, 24)


def test_stop_order_nearest_neighbour(world: None) -> None:
    fx.baler("B1", acres_per_day=20)
    fx.farmer("+919900000002")
    fx.field("F_FAR", acres=4, lng=km_east(BASE_LNG, 6))
    fx.field("F_NEAR", phone="+919900000002", acres=4, lng=km_east(BASE_LNG, 1))
    book_pickup("F_FAR", TODAY)
    near = _booked(book_pickup("F_NEAR", TODAY))
    assert near.stop_order == 1
    orders = {b.field_id: b.stop_order for b in BookingsRepo().list_all()}
    assert orders == {"F_NEAR": 1, "F_FAR": 2}


def test_has_capacity_before_deadline(world: None) -> None:
    fx.baler("B1", acres_per_day=10)
    fx.field("F1", acres=10, deadline=date(2026, 10, 25))
    f = FieldsRepo().get("F1")
    assert f is not None and matching.has_capacity_before_deadline(f, TODAY)
    fx.field("F2", acres=10, deadline=date(2026, 10, 25))
    book_pickup("F2", TODAY)
    assert not matching.has_capacity_before_deadline(f, TODAY)


def test_find_candidates_is_pure_and_sorted() -> None:
    from clearsky.models import Baler, Field

    f = Field(
        field_id="F",
        phone="+91",
        village_id="V",
        acres=5,
        lat=BASE_LAT,
        lng=BASE_LNG,
        harvest_date=date(2026, 10, 22),
        sowing_deadline=date(2026, 10, 27),
        created_at=fx.NOW,
        updated_at=fx.NOW,
    )
    b = Baler(
        baler_id="B",
        operator_name="x",
        base_village_id="V",
        lat=BASE_LAT,
        lng=BASE_LNG,
        acres_per_day=10,
        radius_km=20,
    )
    cands = matching.find_candidates(f, [b], {}, {"B": {date(2026, 10, 24)}}, TODAY)
    assert [c.day for c in cands] == [date(2026, 10, 24), D1, date(2026, 10, 25)]  # cluster day first
    assert cands[0].cluster
