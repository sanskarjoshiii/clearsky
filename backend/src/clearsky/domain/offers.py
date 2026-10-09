"""Offer lifecycle around the matcher: accept, decline, expire, re-offer, escalate.

The matcher (`domain/matching.py`) reserves a baler-day as an OFFER. This module is what happens
next, including the farmer's WhatsApp messages:

    OFFERED ──accept──► CONFIRMED            farmer: "✅ … baler aayega"
       ├──decline──► DECLINED ─┐
       └──timeout──► EXPIRED  ─┴─► the next-best baler gets the offer (that baler never again);
                                   a different date → farmer told the new date;
                                   OFFER_MAX_ATTEMPTS balers asked, or nobody left → the officer's
                                   radar shows "no baler accepted" and the farmer gets the follow-up.

Only farmers are messaged. Balers see offers on their dashboard (`/baler/requests`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from clearsky import clock
from clearsky.agent.rules import HINGLISH, fmt_date
from clearsky.channels import notify
from clearsky.channels.templates import BOOKING_CHANGED, BOOKING_CONFIRMED, BOOKING_DELAYED
from clearsky.config import get_settings
from clearsky.domain import matching, risk
from clearsky.domain.geo import haversine_km
from clearsky.logging import get_logger
from clearsky.models import Baler, Booking, BookingStatus
from clearsky.repo import BalersRepo, BookingsRepo, FarmersRepo, FieldsRepo, VillagesRepo

log = get_logger(child="offers")

DECLINE_REASONS = {
    "machine_unavailable": "Machine not available",
    "too_far": "Too far",
    "day_full": "Already full that day",
    "other": "Other",
}


def _farmer_name(phone: str) -> str:
    farmer = FarmersRepo().get(phone)
    return farmer.name if farmer else ""


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=clock.IST)


def notify_confirmed(bk: Booking) -> None:
    baler = BalersRepo().get(bk.baler_id)
    notify.send_proactive(
        bk.phone,
        BOOKING_CONFIRMED,
        [_farmer_name(bk.phone), fmt_date(bk.date, HINGLISH), baler.operator_name if baler else "-"],
    )


def accept(booking_id: str, baler_id: str | None) -> matching.OfferResult:
    """The baler accepts: the pickup is confirmed and the farmer is told on WhatsApp."""
    result = matching.accept_offer(booking_id, baler_id)
    if result.ok and result.booking is not None:
        notify_confirmed(result.booking)
    elif result.error == "expired" and result.booking is not None:
        _end(result.booking, BookingStatus.EXPIRED)  # too late: move it on right away
    return result


def decline(
    booking_id: str, baler_id: str | None, reason: str, note: str | None = None
) -> tuple[matching.OfferResult, matching.BookingResult | None]:
    """The baler declines with a reason; the field goes to the next-best baler."""
    result = matching.release_offer(booking_id, BookingStatus.DECLINED, baler_id, reason, note)
    if not result.ok or result.booking is None:
        return result, None
    return result, _reoffer(result.booking)


def reassign(booking_id: str) -> tuple[matching.OfferResult, matching.BookingResult | None]:
    """The officer moves an open offer on without waiting for the baler's answer."""
    result = matching.release_offer(booking_id, BookingStatus.EXPIRED, reason="reassigned by officer")
    if not result.ok or result.booking is None:
        return result, None
    return result, _reoffer(result.booking)


def _end(bk: Booking, outcome: BookingStatus) -> matching.BookingResult | None:
    released = matching.release_offer(bk.booking_id, outcome)
    if not released.ok or released.booking is None:
        return None  # accepted, declined or cancelled in the meantime
    return _reoffer(released.booking)


def expire_due(now: datetime | None = None) -> dict[str, int]:
    """The 15-minute job: offers past their SLA expire and are re-offered."""
    now = now or clock.now()
    counts = {"expired": 0, "reoffered": 0, "escalated": 0}
    for bk in BookingsRepo().offered():
        if bk.expires_at is None or _aware(bk.expires_at) > now:
            continue
        _count(_end(bk, BookingStatus.EXPIRED), counts)
    if counts["expired"]:
        log.info("offers expired", extra=counts)
    return counts


def expire_for_baler(baler_id: str) -> dict[str, int]:
    """A baler went off duty: their open offers expire at once and move to other balers."""
    counts = {"expired": 0, "reoffered": 0, "escalated": 0}
    for bk in BookingsRepo().offered():
        if bk.baler_id == baler_id:
            _count(_end(bk, BookingStatus.EXPIRED), counts)
    return counts


def _count(outcome: matching.BookingResult | None, counts: dict[str, int]) -> None:
    if outcome is None:
        return
    counts["expired"] += 1
    counts["reoffered" if isinstance(outcome, matching.Booked) else "escalated"] += 1


def _reoffer(old: Booking) -> matching.BookingResult:
    """Offer the field to the next baler, or escalate to the officer when nobody is left."""
    attempt = old.attempt + 1
    if attempt > get_settings().offer_max_attempts:
        return _escalate(old, f"{old.attempt} balers asked")
    result = matching.book_pickup(old.field_id, attempt=attempt)
    if isinstance(result, matching.NoSlot):
        return _escalate(old, result.reason)
    if result.status == "confirmed":  # AUTO_ACCEPT_DEMO: no baler step
        confirmed = BookingsRepo().get(result.booking_id)
        if confirmed is not None:
            notify_confirmed(confirmed)
    elif result.date != old.date:
        notify.send_proactive(
            old.phone, BOOKING_CHANGED, [_farmer_name(old.phone), fmt_date(result.date, HINGLISH)]
        )
    return result


def _escalate(old: Booking, detail: str) -> matching.NoSlot:
    """Nobody took the field: the radar shows why and the farmer hears that an officer will follow up."""
    risk.refresh_field(old.field_id)
    notify.send_proactive(old.phone, BOOKING_DELAYED, [_farmer_name(old.phone)])
    log.info("offer escalated", extra={"field_id": old.field_id, "detail": detail})
    return matching.NoSlot(field_id=old.field_id, reason="no_baler_accepted", detail=detail)


# ------------------------------------------------------------------ dashboard views


def request_rows(baler: Baler) -> list[dict[str, Any]]:
    """Open offers for one baler (their Requests tab), soonest expiry first."""
    farmers = {f.phone: f for f in FarmersRepo().list_all()}
    villages = {v.village_id: v for v in VillagesRepo().list_all()}
    rows = []
    for bk in BookingsRepo().offered():
        if bk.baler_id != baler.baler_id:
            continue
        farmer = farmers.get(bk.phone)
        village = villages.get(bk.village_id)
        field = FieldsRepo().get(bk.field_id)
        rows.append(
            {
                "booking_id": bk.booking_id,
                "field_id": bk.field_id,
                "date": bk.date.isoformat(),
                "harvest_date": field.harvest_date.isoformat() if field else None,
                "acres": bk.acres,
                "est_tonnes": bk.est_tonnes,
                "lat": bk.lat,
                "lng": bk.lng,
                "farmer_name": farmer.name if farmer else None,
                "village_name": village.name if village else bk.village_id,
                "distance_km": round(haversine_km(baler.lat, baler.lng, bk.lat, bk.lng), 1),
                "offered_at": bk.offered_at.isoformat() if bk.offered_at else None,
                "expires_at": bk.expires_at.isoformat() if bk.expires_at else None,
                "attempt": bk.attempt,
            }
        )
    rows.sort(key=lambda r: (str(r["expires_at"]), str(r["booking_id"])))
    return rows
