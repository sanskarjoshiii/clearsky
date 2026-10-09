"""Phase 5–6: risk scoring, village aggregates, officer alerts, reminders, booking done."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from clearsky.domain import alerts, matching, risk
from clearsky.handlers import processor, reminders
from clearsky.models import BookingStatus, FieldStatus, RiskLevel
from clearsky.repo import BookingsRepo, BuyersRepo, ConversationsRepo, FieldsRepo, VillagesRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load
from tests import factories as fx
from tests.factories import NOW

TODAY = date(2026, 10, 20)


def _field(**kw: object) -> object:
    from clearsky.models import Field

    base = dict(
        field_id="F",
        phone="+91",
        village_id="V",
        acres=5,
        lat=30.0,
        lng=76.0,
        harvest_date=TODAY - timedelta(days=3),
        sowing_deadline=TODAY + timedelta(days=2),
        harvest_confirmed=True,
        status=FieldStatus.HARVESTED,
        created_at=NOW,
        updated_at=NOW,
    )
    base.update(kw)
    return Field(**base)  # type: ignore[arg-type]


def test_score_booked_cleared_and_fire() -> None:
    assert risk.score_field(_field(status=FieldStatus.BOOKED), 1.0, TODAY, False).score == 0  # type: ignore[arg-type]
    assert risk.score_field(_field(status=FieldStatus.CLEARED), 1.0, TODAY, False).reasons == ["cleared"]  # type: ignore[arg-type]
    fire = risk.score_field(_field(status=FieldStatus.FIRE_REPORTED), 0, TODAY, True)  # type: ignore[arg-type]
    assert (fire.score, fire.level) == (100, RiskLevel.RED)


def test_score_formula_and_thresholds() -> None:
    # 2 days to sowing → urgency 0.9; no capacity; history 1.0 → 100*(0.405+0.25+0.30)=95.5 → 96 RED
    r = risk.score_field(_field(), 1.0, TODAY, False)  # type: ignore[arg-type]
    assert (r.score, r.level) == (96, RiskLevel.RED)
    assert r.reasons == [
        "harvested 3 days ago",
        "2 days to sowing",
        "high fire history",
        "no baler free",
        "not booked",
    ]
    # same field, slot available, no history → 0.405 → 40/41 YELLOW
    y = risk.score_field(_field(), 0.0, TODAY, True)  # type: ignore[arg-type]
    assert y.level == RiskLevel.YELLOW and y.score == 40
    # bookable (4 days to sowing) + high fire history → RED (this is why RED is 60, see risk.py)
    b = risk.score_field(_field(sowing_deadline=TODAY + timedelta(days=4)), 1.0, TODAY, True)  # type: ignore[arg-type]
    assert (b.score, b.level) == (66, RiskLevel.RED)
    # not harvested yet → damped by 0.35
    d = risk.score_field(
        _field(
            harvest_confirmed=False, harvest_date=TODAY + timedelta(days=2), status=FieldStatus.REGISTERED
        ),
        1.0,
        TODAY,
        False,
    )  # type: ignore[arg-type]
    assert d.level == RiskLevel.GREEN and d.score == round(100 * 0.955 * 0.35)
    assert risk.level_for(60) == RiskLevel.RED and risk.level_for(59) == RiskLevel.YELLOW
    assert risk.level_for(40) == RiskLevel.YELLOW and risk.level_for(39) == RiskLevel.GREEN


@pytest.fixture
def seeded(ddb: None) -> dict[str, object]:
    data = generate(42)
    load(data, prebook=True)
    return data


def _with_fire_history(score: float = 1.0) -> None:
    for v in VillagesRepo().list_all():
        VillagesRepo().update_fields(v.village_id, {"fire_history_score": score})


def test_run_all_seed_has_red_fields_once_fire_history_exists(seeded: dict[str, object]) -> None:
    """PLAN Phase 6 DoD: ≥ 5 RED fields in Sangrur (fire history from FIRMS)."""
    no_history = risk.run_all(TODAY)
    _with_fire_history(1.0)
    counts = risk.run_all(TODAY)
    assert counts["red"] >= 5 and counts["red"] > no_history["red"]
    reds = FieldsRepo().by_status(FieldStatus.HARVESTED)
    assert all(
        f.risk_level == RiskLevel.RED for f in reds if f.field_id in seeded["meta"]["red_candidate_field_ids"]
    )  # type: ignore[index]
    v = max(VillagesRepo().list_all(), key=lambda v: v.risk_red_fields)
    assert v.risk_red_fields >= 1 and v.risk_max_score >= 60 and v.risk_unbooked_acres > 0


def test_alert_notifies_unbooked_farmers_and_flags_balers(seeded: dict[str, object]) -> None:
    _with_fire_history(1.0)
    risk.run_all(TODAY)
    village = max(VillagesRepo().list_all(), key=lambda v: v.risk_red_fields)
    open_fields = [
        f
        for f in FieldsRepo().by_village(village.village_id)
        if f.status in (FieldStatus.REGISTERED, FieldStatus.HARVESTED)
    ]
    result = alerts.create_alert(village.village_id, "officer-1", TODAY)
    assert result.farmers_notified == len({f.phone for f in open_fields}) > 0
    assert result.balers_flagged and not result.cooldown
    turn = ConversationsRepo().last(open_fields[0].phone, 1)[0]
    assert turn.kind == "buttons" and turn.buttons[0].id.startswith("alertbook:")
    # cooldown: a second alert within 30 min returns the first one
    again = alerts.create_alert(village.village_id, "officer-1", TODAY)
    assert again.cooldown and again.alert.alert_id == result.alert.alert_id
    # flagged operators see it on their dashboard
    assert alerts.open_alerts_for_baler(result.balers_flagged[0])[0].village_id == village.village_id


def test_alert_haan_books_and_turns_green(seeded: dict[str, object]) -> None:
    """PLAN Phase 6 DoD: tapping HAAN books the field and its level becomes GREEN in one request."""
    _with_fire_history(1.0)
    risk.run_all(TODAY)
    red = next(f for f in FieldsRepo().by_status(FieldStatus.HARVESTED) if f.risk_level == RiskLevel.RED)
    alerts.create_alert(red.village_id, "officer-1", TODAY)
    turn = ConversationsRepo().last(red.phone, 1)[0]
    from clearsky.channels.whatsapp import Inbound

    sent = processor.process_inbound(
        Inbound(
            msg_id="h1", phone=red.phone, type="button", button_id=turn.buttons[0].id, text="HAAN, book karo"
        )
    )
    after = FieldsRepo().get(red.field_id)
    assert after is not None and after.status == FieldStatus.BOOKED and after.risk_level == RiskLevel.GREEN
    # the tap creates an offer: the field is BOOKED (green) at once, confirmation follows on accept
    assert after.booking_state == "offered"
    assert sent[0].startswith("📨") or "baler khali nahi" in sent[0]


def test_cancel_and_confirm_refresh_risk(seeded: dict[str, object]) -> None:
    fx.farmer("+919900000500", village_id="V002")
    fx.field(
        "FR",
        phone="+919900000500",
        village_id="V002",
        harvest=TODAY - timedelta(days=1),
        deadline=TODAY + timedelta(days=4),
        lat=30.266,
        lng=76.039,
    )
    booked = matching.book_pickup("FR", TODAY)
    assert isinstance(booked, matching.Booked)
    assert FieldsRepo().get("FR").risk_reasons == ["booked"]  # type: ignore[union-attr]
    matching.cancel_booking(booked.booking_id, TODAY)
    f = FieldsRepo().get("FR")
    assert f is not None and "not booked" in f.risk_reasons and f.risk_score > 0


def test_mark_done_flow(seeded: dict[str, object]) -> None:
    bk = next(b for b in BookingsRepo().list_all() if b.status == BookingStatus.CONFIRMED)
    other = next(b for b in ("B01", "B02", "B03") if b != bk.baler_id)
    assert matching.mark_done(bk.booking_id, other).error == "forbidden"
    received_before = BuyersRepo().get(bk.buyer_id).received_tonnes if bk.buyer_id else 0  # type: ignore[union-attr]
    done = matching.mark_done(bk.booking_id, bk.baler_id)
    assert done.ok
    assert BookingsRepo().get(bk.booking_id).status == BookingStatus.DONE  # type: ignore[union-attr]
    assert FieldsRepo().get(bk.field_id).status == FieldStatus.CLEARED  # type: ignore[union-attr]
    if bk.buyer_id:
        assert BuyersRepo().get(bk.buyer_id).received_tonnes == pytest.approx(received_before + bk.est_tonnes)  # type: ignore[union-attr]
    assert matching.mark_done(bk.booking_id, bk.baler_id).error == "not_confirmed"
    assert matching.mark_done("nope").error == "not_found"


def test_reminders_select_tomorrow_and_run_once(seeded: dict[str, object]) -> None:
    tomorrow = TODAY + timedelta(days=1)
    fx.farmer("+919900000600", village_id="V002", name="Kuldeep")
    fx.field("FH", phone="+919900000600", village_id="V002", harvest=tomorrow, lat=30.266, lng=76.039)
    expected_pickups = [b for b in BookingsRepo().by_date(tomorrow) if b.status == BookingStatus.CONFIRMED]
    expected_checks = [
        f
        for f in FieldsRepo().list_all()
        if f.harvest_date == tomorrow
        and not f.harvest_confirmed
        and f.status in (FieldStatus.REGISTERED, FieldStatus.BOOKED)
    ]
    summary = reminders.run(TODAY)
    assert summary == {
        "harvest_checks": len(expected_checks),
        "pickup_notices": len(expected_pickups),
        "skipped": 0,
    }
    turn = ConversationsRepo().last("+919900000600", 1)[0]
    assert "Kuldeep ji" in turn.text and [b.title for b in turn.buttons] == ["HAAN", "NAHI"]
    assert reminders.run(TODAY)["skipped"] == 1
    assert reminders.run(TODAY, force=True)["skipped"] == 0
