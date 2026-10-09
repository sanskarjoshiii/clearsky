"""Issue #3: balers accept or decline assigned fields (offer → accept / decline / expire → re-offer)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from clearsky import clock
from clearsky.config import reset_settings
from clearsky.domain import matching, offers, risk
from clearsky.domain.matching import Booked, NoSlot, book_pickup
from clearsky.handlers import offers_job, reminders
from clearsky.models import BookingStatus, FieldStatus
from clearsky.repo import BalerDaysRepo, BookingsRepo, BuyersRepo, ConversationsRepo, FieldsRepo
from tests import factories as fx
from tests.apiclient import BUYER, OFFICER, call, operator
from tests.factories import BASE_LNG, km_east

TODAY = date(2026, 10, 20)
D1 = date(2026, 10, 23)  # first bookable day for a field harvested on Oct 22
PHONE = "+919900000001"


@pytest.fixture
def world(ddb: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """One farmer with one field, and two balers: B1 next to the field, B2 two km away."""
    monkeypatch.setenv("DEV_AUTH", "true")
    reset_settings()
    fx.village("V1", "Testpur")
    fx.farmer(PHONE, name="Gurpreet")
    fx.baler("B1")
    fx.baler("B2", lng=km_east(BASE_LNG, 2))
    fx.buyer("BY1")
    fx.field("F1")


def offer(field_id: str = "F1") -> Booked:
    r = book_pickup(field_id, TODAY)
    assert isinstance(r, Booked), r
    return r


def last_message(phone: str = PHONE) -> str:
    turns = ConversationsRepo().last(phone, 1)
    return turns[0].text if turns else ""


def booking(booking_id: str) -> matching.Booking:
    bk = BookingsRepo().get(booking_id)
    assert bk is not None
    return bk


# ------------------------------------------------------------------ offer


def test_a_new_booking_is_an_offer_that_reserves_capacity(world: None) -> None:
    r = offer()
    assert (r.status, r.baler_id, r.date, r.stop_order, r.attempt) == ("offered", "B1", D1, 0, 1)
    bk = booking(r.booking_id)
    assert bk.status == BookingStatus.OFFERED and bk.offered_at is not None and bk.expires_at is not None
    assert timedelta(0) < bk.expires_at - clock.now() <= timedelta(minutes=120)
    field = FieldsRepo().get("F1")
    # the field counts as booked (radar green) while the offer is open, so it can't be offered twice
    assert field is not None and field.status == FieldStatus.BOOKED and field.booking_state == "offered"
    assert field.risk_level.value == "GREEN"
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and day.booked_acres == 8  # reserved at offer time: no overbooking
    assert BuyersRepo().get("BY1").reserved_tonnes == 20  # type: ignore[union-attr]
    again = book_pickup("F1", TODAY)
    assert isinstance(again, Booked) and again.already_booked and again.booking_id == r.booking_id


def test_offer_expiry_is_capped_at_the_start_of_the_pickup_day(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OFFER_SLA_MINUTES", str(60 * 24 * 30))
    reset_settings()
    bk = booking(offer().booking_id)
    assert bk.expires_at is not None
    assert (bk.expires_at.date(), bk.expires_at.hour, bk.expires_at.minute) == (D1, 0, 0)


def test_auto_accept_keeps_the_instant_booking(world: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTO_ACCEPT_DEMO", "true")
    reset_settings()
    r = offer()
    assert (r.status, r.stop_order) == ("confirmed", 1)
    assert booking(r.booking_id).status == BookingStatus.CONFIRMED
    assert FieldsRepo().get("F1").booking_state == "confirmed"  # type: ignore[union-attr]


def test_baler_sees_the_offer_as_a_request_not_on_the_route(world: None) -> None:
    r = offer()
    status, body = call("GET", "/api/operator/me/requests", token=operator("B1"))
    assert status == 200 and [x["booking_id"] for x in body["requests"]] == [r.booking_id]
    row = body["requests"][0]
    assert (row["farmer_name"], row["village_name"], row["acres"], row["date"]) == (
        "Gurpreet",
        "Testpur",
        8,
        "2026-10-23",
    )
    assert row["distance_km"] == 0 and row["expires_at"] and "farmer_phone" not in row and "phone" not in row
    assert {r["value"] for r in body["reasons"]} == set(offers.DECLINE_REASONS)
    assert call("GET", "/api/operator/me/requests", token=operator("B2"))[1]["requests"] == []
    assert call("GET", "/api/operator/me/requests", token=BUYER)[0] == 403
    route = call("GET", "/api/operator/me/route", token=operator("B1"), query={"date": "2026-10-23"})[1]
    assert route["stops"] == []
    assert call("GET", "/api/operator/me", token=operator("B1"))[1]["baler"]["open_requests"] == 1
    # an offer can't be marked done
    assert call("POST", f"/api/bookings/{r.booking_id}/done", token=operator("B1"))[0] == 409


# ------------------------------------------------------------------ accept


def test_accept_confirms_and_tells_the_farmer(world: None) -> None:
    r = offer()
    assert call("POST", f"/api/bookings/{r.booking_id}/accept", token=operator("B2"))[0] == 403
    assert call("POST", f"/api/bookings/{r.booking_id}/accept", token=OFFICER)[0] == 403
    status, body = call("POST", f"/api/bookings/{r.booking_id}/accept", token=operator("B1"))
    assert status == 200 and body["booking"]["status"] == "CONFIRMED" and body["booking"]["stop_order"] == 1
    assert "phone" not in body["booking"]
    bk = booking(r.booking_id)
    assert bk.status == BookingStatus.CONFIRMED and bk.responded_at is not None and bk.stop_order == 1
    assert FieldsRepo().get("F1").booking_state == "confirmed"  # type: ignore[union-attr]
    assert (
        last_message()
        == "✅ Gurpreet ji, 23 Oct ko baler Operator B1 aapka khet saaf karne aayega. Parali na jalayein. 🙏"
    )
    # now it is a stop on the route, and the request is gone
    route = call("GET", "/api/operator/me/route", token=operator("B1"), query={"date": "2026-10-23"})[1]
    assert [s["booking_id"] for s in route["stops"]] == [r.booking_id]
    assert call("GET", "/api/operator/me/requests", token=operator("B1"))[1]["requests"] == []
    second = call("POST", f"/api/bookings/{r.booking_id}/accept", token=operator("B1"))
    assert second[0] == 409 and second[1]["error"]["code"] == "not_offered"
    assert call("POST", "/api/bookings/BK-nope/accept", token=operator("B1"))[0] == 404
    # done still works, from CONFIRMED only
    assert call("POST", f"/api/bookings/{r.booking_id}/done", token=operator("B1"))[0] == 200


# ------------------------------------------------------------------ decline → next baler


def test_decline_releases_capacity_and_offers_the_next_baler(world: None) -> None:
    r = offer()
    bad = call("POST", f"/api/bookings/{r.booking_id}/decline", {"reason": "bored"}, token=operator("B1"))
    assert bad[0] == 400
    assert call("POST", f"/api/bookings/{r.booking_id}/decline", {}, token=operator("B1"))[0] == 400
    forbidden = call(
        "POST", f"/api/bookings/{r.booking_id}/decline", {"reason": "too_far"}, token=operator("B2")
    )
    assert forbidden[0] == 403
    status, body = call(
        "POST",
        f"/api/bookings/{r.booking_id}/decline",
        {"reason": "machine_unavailable", "note": "gearbox"},
        token=operator("B1"),
    )
    assert status == 200 and body["booking"]["status"] == "DECLINED"
    declined = booking(r.booking_id)
    assert (declined.status, declined.decline_reason, declined.decline_note) == (
        BookingStatus.DECLINED,
        "machine_unavailable",
        "gearbox",
    )
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and (day.booked_acres, day.stop_count) == (0, 0)  # B1's day is free again

    field = FieldsRepo().get("F1")
    assert field is not None and field.status == FieldStatus.BOOKED and field.booking_id != r.booking_id
    nxt = booking(field.booking_id or "")
    assert (nxt.baler_id, nxt.status, nxt.attempt, nxt.date) == ("B2", BookingStatus.OFFERED, 2, D1)
    assert BuyersRepo().get("BY1").reserved_tonnes == 20  # type: ignore[union-attr]  # released, then reserved once
    # same date with the new baler: the farmer is not bothered until someone accepts
    assert not last_message().startswith("📨")
    assert (
        call("POST", f"/api/bookings/{r.booking_id}/decline", {"reason": "too_far"}, token=operator("B1"))[0]
        == 409
    )


def test_the_declining_baler_never_gets_that_field_again(world: None) -> None:
    first = offer()
    offers.decline(first.booking_id, "B1", "too_far")
    second = booking(FieldsRepo().get("F1").booking_id or "")  # type: ignore[union-attr]
    assert second.baler_id == "B2"
    # B2 declines too: B1 is the only baler left but already said no → escalate, don't bounce back
    _, outcome = offers.decline(second.booking_id, "B2", "day_full")
    assert isinstance(outcome, NoSlot) and outcome.reason == "no_baler_accepted"
    field = FieldsRepo().get("F1")
    assert field is not None and field.status == FieldStatus.REGISTERED and field.booking_id is None
    assert "no baler accepted" in field.risk_reasons  # the officer's radar says why
    assert matching.refused_balers("F1") == {"B1", "B2"}
    assert last_message().startswith("Gurpreet ji, abhi tak kisi baler ne aapki pickup confirm nahi ki")
    day1, day2 = BalerDaysRepo().get("B1", D1), BalerDaysRepo().get("B2", D1)
    assert day1 is not None and day2 is not None and day1.booked_acres == day2.booked_acres == 0
    assert BuyersRepo().get("BY1").reserved_tonnes == 0  # type: ignore[union-attr]
    # even a fresh request from the farmer skips the balers who refused
    again = book_pickup("F1", TODAY)
    assert isinstance(again, NoSlot) and again.reason == "no_baler_capacity"


def test_escalates_after_max_attempts_even_if_balers_remain(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OFFER_MAX_ATTEMPTS", "2")
    reset_settings()
    fx.baler("B3", lng=km_east(BASE_LNG, 4))
    first = offer()
    offers.decline(first.booking_id, "B1", "too_far")
    second = booking(FieldsRepo().get("F1").booking_id or "")  # type: ignore[union-attr]
    assert (second.baler_id, second.attempt) == ("B2", 2)
    _, outcome = offers.decline(second.booking_id, "B2", "too_far")
    assert isinstance(outcome, NoSlot) and outcome.reason == "no_baler_accepted"
    assert not any(b.baler_id == "B3" for b in BookingsRepo().list_all())
    field = FieldsRepo().get("F1")
    assert field is not None and field.status == FieldStatus.REGISTERED
    # B3 is still free, so the radar says how many balers refused rather than "no baler free"
    assert "declined by 2 balers" in field.risk_reasons


def test_reoffer_on_a_different_date_tells_the_farmer(world: None) -> None:
    fx.baler("B2", lng=km_east(BASE_LNG, 1))  # 1 km away: cheaper than waiting a day for B1
    fx.farmer("+919900000002", name="Other")
    fx.field("F_BLOCK", phone="+919900000002", acres=12)
    blocker = book_pickup("F_BLOCK", TODAY, auto_accept=True)  # fills B1's first day
    assert isinstance(blocker, Booked) and (blocker.baler_id, blocker.date) == ("B1", D1)
    first = offer()  # 8 acres don't fit B1 on D1 any more → nearest free: B2 on D1
    assert (first.baler_id, first.date) == ("B2", D1)
    _, outcome = offers.decline(first.booking_id, "B2", "day_full")
    assert isinstance(outcome, Booked) and (outcome.baler_id, outcome.date) == ("B1", date(2026, 10, 24))
    assert last_message() == (
        "📨 Gurpreet ji, aapki pickup ki tareekh badal kar 24 Oct ho gayi hai. Baler ke confirm karte hi batayenge."
    )


# ------------------------------------------------------------------ expiry


def test_unanswered_offers_expire_and_move_on(world: None) -> None:
    r = offer()
    assert offers.expire_due() == {"expired": 0, "reoffered": 0, "escalated": 0}  # not due yet
    assert booking(r.booking_id).status == BookingStatus.OFFERED
    later = clock.now() + timedelta(minutes=121)
    assert offers.expire_due(later) == {"expired": 1, "reoffered": 1, "escalated": 0}
    assert booking(r.booking_id).status == BookingStatus.EXPIRED
    nxt = booking(FieldsRepo().get("F1").booking_id or "")  # type: ignore[union-attr]
    assert (nxt.baler_id, nxt.status, nxt.attempt) == ("B2", BookingStatus.OFFERED, 2)
    assert matching.refused_balers("F1") == {"B1"}  # a baler who ignored it isn't asked again either
    # the scheduled Lambda does the same thing
    assert offers_job.handler({}, None) == {"expired": 0, "reoffered": 0, "escalated": 0}


def test_accepting_too_late_is_refused_and_the_offer_moves_on(
    world: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    r = offer()
    real_now = clock.now
    monkeypatch.setattr(clock, "now", lambda: real_now() + timedelta(minutes=121))
    status, body = call("POST", f"/api/bookings/{r.booking_id}/accept", token=operator("B1"))
    assert status == 409 and body["error"]["code"] == "expired"
    assert booking(r.booking_id).status == BookingStatus.EXPIRED
    assert booking(FieldsRepo().get("F1").booking_id or "").baler_id == "B2"  # type: ignore[union-attr]


def test_off_duty_baler_loses_open_offers_at_once(world: None) -> None:
    r = offer()
    status, body = call("PUT", "/api/operator/me", {"active": False}, token=operator("B1"))
    assert status == 200 and body["baler"]["active"] is False
    assert booking(r.booking_id).status == BookingStatus.EXPIRED
    assert booking(FieldsRepo().get("F1").booking_id or "").baler_id == "B2"  # type: ignore[union-attr]
    # the officer switching a baler off does the same
    moved = call("POST", "/api/balers/B2/active", {"active": False}, token=OFFICER)[1]
    assert moved["offers_moved"] == {"expired": 1, "reoffered": 0, "escalated": 1}
    assert FieldsRepo().get("F1").status == FieldStatus.REGISTERED  # type: ignore[union-attr]


def test_officer_can_reassign_an_open_offer(world: None) -> None:
    r = offer()
    assert call("POST", f"/api/bookings/{r.booking_id}/reassign", token=operator("B1"))[0] == 403
    status, body = call("POST", f"/api/bookings/{r.booking_id}/reassign", token=OFFICER)
    assert status == 200 and body["booking"]["status"] == "EXPIRED"
    assert (body["next"]["baler_id"], body["next"]["status"]) == ("B2", "offered")
    assert call("POST", f"/api/bookings/{r.booking_id}/reassign", token=OFFICER)[0] == 409


# ------------------------------------------------------------------ races: exactly one outcome


def test_accept_and_expiry_racing_have_one_winner(world: None) -> None:
    r = offer()
    stale = booking(r.booking_id)  # the expiry job read the offer before the baler accepted
    assert matching.accept_offer(r.booking_id, "B1").ok
    assert not matching._release(stale, BookingStatus.EXPIRED, TODAY)  # the conditional write stops it
    assert booking(r.booking_id).status == BookingStatus.CONFIRMED
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and (day.booked_acres, day.stop_count) == (8, 1)

    fx.field("F2", acres=4)
    other = offer("F2")
    stale2 = booking(other.booking_id)
    assert matching._release(stale2, BookingStatus.EXPIRED, TODAY)  # expiry wins this time
    late = matching.accept_offer(other.booking_id, "B1")
    assert not late.ok and late.error == "not_offered"
    assert matching.accept_offer(other.booking_id, "B1").error == "not_offered"
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and (day.booked_acres, day.stop_count) == (8, 1)  # only F1's acres remain


def test_decline_twice_releases_capacity_once(world: None) -> None:
    r = offer()
    stale = booking(r.booking_id)
    assert matching._release(stale, BookingStatus.DECLINED, TODAY)
    assert not matching._release(stale, BookingStatus.DECLINED, TODAY)
    day = BalerDaysRepo().get("B1", D1)
    assert day is not None and (day.booked_acres, day.stop_count) == (0, 0)
    assert BuyersRepo().get("BY1").reserved_tonnes == 0  # type: ignore[union-attr]


# ------------------------------------------------------------------ farmer changes while an offer is open


def test_farmer_cancel_and_reschedule_release_the_open_offer(world: None) -> None:
    r = offer()
    assert matching.cancel_booking(r.booking_id, TODAY)
    assert booking(r.booking_id).status == BookingStatus.CANCELLED
    day = BalerDaysRepo().get("B1", D1)
    field = FieldsRepo().get("F1")
    assert day is not None and day.booked_acres == 0
    assert field is not None and field.status == FieldStatus.REGISTERED and field.booking_state is None

    again = offer()
    moved = matching.reschedule("F1", date(2026, 10, 30), TODAY)
    assert isinstance(moved, Booked) and moved.status == "offered" and moved.date == date(2026, 10, 31)
    assert booking(again.booking_id).status == BookingStatus.CANCELLED
    assert BalerDaysRepo().get("B1", D1).booked_acres == 0  # type: ignore[union-attr]
    assert matching.refused_balers("F1") == set()  # a farmer's own change is not a baler refusal


# ------------------------------------------------------------------ only confirmed work counts


def test_route_stats_supply_and_reminders_ignore_open_offers(world: None) -> None:
    r = offer()
    stats = call("GET", "/api/stats")[1]
    assert (stats["bookings"], stats["acres_booked"], stats["tonnes_booked"]) == (0, 0, 0)
    assert (stats["offers_waiting"], stats["acres_offered"]) == (1, 8)
    assert call("GET", "/api/buyers/me/supply", token="dev.buyer.BY1")[1]["deliveries"] == []
    schedule = call("GET", "/api/operator/me/schedule", token=operator("B1"))[1]["days"]
    assert next(d for d in schedule if d["date"] == "2026-10-23")["stops"] == 0
    # the evening before the pickup day: no "baler aayega" for an offer nobody accepted
    assert reminders.run(D1 - timedelta(days=1), force=True)["pickup_notices"] == 0

    offers.accept(r.booking_id, "B1")
    stats = call("GET", "/api/stats")[1]
    assert (stats["bookings"], stats["acres_booked"], stats["offers_waiting"]) == (1, 8, 0)
    assert len(call("GET", "/api/buyers/me/supply", token="dev.buyer.BY1")[1]["deliveries"]) == 1
    assert reminders.run(D1 - timedelta(days=1), force=True)["pickup_notices"] == 1


def test_officer_sees_the_offer_timeline_on_the_field(world: None) -> None:
    first = offer()
    offers.decline(first.booking_id, "B1", "too_far", "bridge closed")
    detail = call("GET", "/api/fields/F1", token=OFFICER)[1]
    assert detail["booking_state"] == "offered"
    timeline = [(b["operator_name"], b["status"], b.get("decline_reason")) for b in detail["bookings"]]
    assert timeline == [("Operator B1", "DECLINED", "too_far"), ("Operator B2", "OFFERED", None)]
    assert detail["bookings"][0]["decline_note"] == "bridge closed"
    rows = call("GET", "/api/bookings", token=OFFICER)[1]["bookings"]
    assert {b["status"] for b in rows} == {"DECLINED", "OFFERED"}


def test_risk_reasons_explain_refusals() -> None:
    f = fx.Field(
        field_id="F",
        phone="+91",
        village_id="V",
        acres=5,
        lat=0,
        lng=0,
        harvest_date=date(2026, 10, 18),
        sowing_deadline=date(2026, 10, 30),
        status=FieldStatus.HARVESTED,
        created_at=fx.NOW,
        updated_at=fx.NOW,
    )
    assert "no baler accepted" in risk.score_field(f, 0.0, TODAY, slot_available=False, refused=2).reasons
    assert "no baler free" in risk.score_field(f, 0.0, TODAY, slot_available=False).reasons
    assert "declined by 1 baler" in risk.score_field(f, 0.0, TODAY, slot_available=True, refused=1).reasons
