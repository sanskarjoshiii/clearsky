"""Matching and booking engine (IMPLEMENTATION.md §4).

Pure functions choose a baler-day and a buyer; `book_pickup` commits the choice with one DynamoDB
transaction, so two concurrent requests can never over-book a baler-day or a buyer.

A booking starts as an OFFER to the chosen baler (capacity is reserved at once). The baler accepts
(`accept_offer` → CONFIRMED) or the offer ends (`release_offer` → DECLINED / EXPIRED, capacity
released). `domain/offers.py` adds the farmer messages and the re-offer to the next baler.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel

from clearsky import clock
from clearsky.config import get_settings
from clearsky.domain import impact
from clearsky.domain.geo import haversine_km
from clearsky.domain.pricing import Quote, estimate_tonnes, quote
from clearsky.logging import get_logger
from clearsky.models import (
    Baler,
    BalerDay,
    Booking,
    BookingStatus,
    Buyer,
    Field,
    FieldStatus,
    to_item,
)
from clearsky.models.enums import BOOKABLE_STATUSES, OPEN_BOOKING_STATUSES, REFUSED_BOOKING_STATUSES
from clearsky.repo import BalerDaysRepo, BalersRepo, BookingsRepo, BuyersRepo, FieldsRepo
from clearsky.repo.transactions import TransactionCancelled, TxBuilder

log = get_logger(child="matching")

# Positions of operations inside the booking transaction (used to read cancellation reasons).
_TX_CAPACITY, _TX_BOOKING, _TX_FIELD, _TX_BUYER = 0, 1, 2, 3


# ----------------------------------------------------------------- results


class Booked(BaseModel):
    kind: Literal["booked"] = "booked"
    booking_id: str
    field_id: str
    date: date
    stop_order: int
    baler_id: str
    operator_name: str
    chc_name: str
    buyer_id: str | None
    buyer_name: str | None
    acres: float
    est_tonnes: float
    farmer_payout: float
    free_clearance: bool
    already_booked: bool = False
    # "offered": waiting for the baler to accept; nobody may tell the farmer it is confirmed yet
    status: Literal["offered", "confirmed"] = "confirmed"
    expires_at: datetime | None = None
    attempt: int = 1


class NoSlot(BaseModel):
    kind: Literal["no_slot"] = "no_slot"
    field_id: str
    reason: Literal[
        "not_found",
        "not_bookable",
        "deadline_too_close",
        "no_baler_capacity",
        "contention",
        "no_baler_accepted",
    ]
    detail: str = ""


BookingResult = Booked | NoSlot


# ------------------------------------------------------------- pure logic


@dataclass(frozen=True)
class Candidate:
    score: float
    baler: Baler
    day: date
    dist_km: float
    cluster: bool
    booked_acres: float


def compute_sowing_deadline(harvest_date: date, sowing_date: date | None = None) -> date:
    s = get_settings()
    if sowing_date is not None:
        return min(sowing_date, s.season_sowing_cutoff)
    return min(harvest_date + timedelta(days=s.sowing_window_days), s.season_sowing_cutoff)


def booking_window(field: Field, today: date) -> tuple[date, date]:
    start = max(field.harvest_date + timedelta(days=1), today + timedelta(days=1))
    end = field.sowing_deadline - timedelta(days=get_settings().sowing_buffer_days)
    return start, end


def balers_in_range(field: Field, balers: list[Baler]) -> list[tuple[Baler, float]]:
    out = []
    for b in balers:
        if not b.active:
            continue
        d = haversine_km(field.lat, field.lng, b.lat, b.lng)
        if d <= b.radius_km:
            out.append((b, d))
    return out


def fits(acres: float, capacity: float, booked: float) -> bool:
    """A field fits if there's room. A field bigger than a whole day only fits an empty day."""
    if acres > capacity:
        return booked == 0
    return capacity - booked >= acres


def find_candidates(
    field: Field,
    balers: list[Baler],
    ledger: dict[str, dict[date, BalerDay]],
    village_days: dict[str, set[date]],
    today: date,
) -> list[Candidate]:
    """All feasible (baler, day) pairs, best (lowest score) first.

    ledger[baler_id][day] is the capacity ledger; village_days[baler_id] holds days on which that
    baler already has a stop in the field's village (cluster bonus).
    """
    s = get_settings()
    start, end = booking_window(field, today)
    if start > end:
        return []
    out: list[Candidate] = []
    for baler, dist in balers_in_range(field, balers):
        days = ledger.get(baler.baler_id, {})
        d = start
        while d <= end:
            booked = days[d].booked_acres if d in days else 0.0
            if fits(field.acres, baler.acres_per_day, booked):
                delay = (d - start).days
                cluster = d in village_days.get(baler.baler_id, set())
                score = s.w_dist * dist + s.w_delay * delay - s.w_cluster * (1 if cluster else 0)
                out.append(Candidate(round(score, 4), baler, d, round(dist, 2), cluster, booked))
            d += timedelta(days=1)
    out.sort(key=lambda c: (c.score, c.baler.baler_id, c.day))
    return out


def choose_buyer(field: Field, tonnes: float, buyers: list[Buyer]) -> tuple[Buyer, float] | None:
    """Buyer with the best net price (price − transport) among those with room and in radius."""
    best: tuple[float, Buyer, float] | None = None
    for b in buyers:
        if b.remaining_tonnes < tonnes:
            continue
        net, dist = net_price(b, field.lat, field.lng)
        if dist > b.max_radius_km:
            continue
        if best is None or net > best[0] or (net == best[0] and b.buyer_id < best[1].buyer_id):
            best = (net, b, dist)
    return (best[1], round(best[2], 2)) if best else None


def nearest_neighbour_order(start: tuple[float, float], stops: list[Booking]) -> list[Booking]:
    remaining = list(stops)
    ordered: list[Booking] = []
    here = start
    while remaining:
        nxt = min(remaining, key=lambda b: (haversine_km(here[0], here[1], b.lat, b.lng), b.booking_id))
        ordered.append(nxt)
        remaining.remove(nxt)
        here = (nxt.lat, nxt.lng)
    return ordered


# -------------------------------------------------------------- data access


def refused_balers(field_id: str) -> set[str]:
    """Balers that declined this field or let its offer expire: they are never offered it again."""
    return {b.baler_id for b in BookingsRepo().by_field(field_id) if b.status in REFUSED_BOOKING_STATUSES}


def _load_candidates(field: Field, today: date) -> list[Candidate]:
    start, end = booking_window(field, today)
    if start > end:
        return []
    refused = refused_balers(field.field_id)
    balers = [b for b, _ in balers_in_range(field, BalersRepo().list_active()) if b.baler_id not in refused]
    days_repo, bookings_repo = BalerDaysRepo(), BookingsRepo()
    ledger: dict[str, dict[date, BalerDay]] = {}
    village_days: dict[str, set[date]] = {}
    for b in balers:
        ledger[b.baler_id] = days_repo.range(b.baler_id, start, end)
        village_days[b.baler_id] = {
            bk.date
            for bk in bookings_repo.by_baler(b.baler_id, start, end)
            if bk.village_id == field.village_id and bk.status in OPEN_BOOKING_STATUSES
        }
    return find_candidates(field, balers, ledger, village_days, today)


def has_capacity_before_deadline(field: Field, today: date | None = None) -> bool:
    """Cheap check used by the risk engine: could this field be booked right now?"""
    return bool(_load_candidates(field, today or clock.today()))


def _existing_booked(field: Field) -> Booked | None:
    if field.status != FieldStatus.BOOKED or not field.booking_id:
        return None
    bk = BookingsRepo().get(field.booking_id)
    if bk is None or bk.status not in OPEN_BOOKING_STATUSES:
        return None
    baler = BalersRepo().get(bk.baler_id)
    buyer = BuyersRepo().get(bk.buyer_id) if bk.buyer_id else None
    return _to_booked(bk, baler, buyer, already=True)


def _to_booked(bk: Booking, baler: Baler | None, buyer: Buyer | None, already: bool = False) -> Booked:
    return Booked(
        booking_id=bk.booking_id,
        field_id=bk.field_id,
        date=bk.date,
        stop_order=bk.stop_order,
        baler_id=bk.baler_id,
        operator_name=baler.operator_name if baler else "",
        chc_name=baler.chc_name if baler else "",
        buyer_id=bk.buyer_id,
        buyer_name=buyer.name if buyer else None,
        acres=bk.acres,
        est_tonnes=bk.est_tonnes,
        farmer_payout=bk.farmer_payout,
        free_clearance=bk.farmer_payout <= 0,
        already_booked=already,
        status="offered" if bk.status == BookingStatus.OFFERED else "confirmed",
        expires_at=bk.expires_at,
        attempt=bk.attempt,
    )


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=clock.IST)


def offer_expiry(day: date) -> datetime:
    """An offer must be answered within the SLA, and in any case before its pickup day starts."""
    sla = clock.now() + timedelta(minutes=get_settings().offer_sla_minutes)
    return min(sla, datetime.combine(day, time.min, tzinfo=clock.IST))


# ------------------------------------------------------------------ commands


def book_pickup(
    field_id: str, today: date | None = None, *, auto_accept: bool | None = None, attempt: int = 1
) -> BookingResult:
    """Reserve the best baler-day for a field.

    The booking is an OFFER the baler must accept, unless `auto_accept` (default: the
    AUTO_ACCEPT_DEMO setting) confirms it at once. `attempt` counts the balers asked so far.
    """
    today = today or clock.today()
    s = get_settings()
    auto = s.auto_accept_demo if auto_accept is None else auto_accept
    fields = FieldsRepo()
    field = fields.get(field_id)
    if field is None:
        return NoSlot(field_id=field_id, reason="not_found")
    if field.status not in BOOKABLE_STATUSES:
        existing = _existing_booked(field)
        if existing:
            return existing
        return NoSlot(field_id=field_id, reason="not_bookable", detail=f"status {field.status.value}")

    start, end = booking_window(field, today)
    if start > end:
        return NoSlot(field_id=field_id, reason="deadline_too_close", detail=f"window {start}..{end}")

    candidates = _load_candidates(field, today)
    if not candidates:
        return NoSlot(field_id=field_id, reason="no_baler_capacity", detail=f"window {start}..{end}")

    tonnes = estimate_tonnes(field.acres)
    buyers = BuyersRepo().list_all()
    for cand in candidates[: s.matcher_max_attempts]:
        chosen = choose_buyer(field, tonnes, buyers)
        buyer, buyer_dist = chosen if chosen else (None, None)
        q = quote(field.acres, buyer.price_per_tonne if buyer else None, buyer_dist)
        booking = _new_booking(field, cand, buyer, q, offered=not auto, attempt=attempt)
        try:
            _commit(field, cand, buyer, booking)
        except TransactionCancelled as e:
            idx = e.failed_index()
            log.info("booking conflict", extra={"field_id": field_id, "op": idx, "reasons": e.reasons})
            if idx == _TX_FIELD:
                fresh = fields.get(field_id)
                existing = _existing_booked(fresh) if fresh else None
                if existing:
                    return existing
                return NoSlot(field_id=field_id, reason="not_bookable", detail="field changed")
            if idx == _TX_BUYER:
                buyers = BuyersRepo().list_all()  # demand moved; re-choose on the next attempt
            continue
        if auto:  # an offer joins the route (and gets its stop number) only when the baler accepts
            ordered = recompute_stop_order(cand.baler.baler_id, cand.day)
            stop = next((b.stop_order for b in ordered if b.booking_id == booking.booking_id), 0)
            booking = booking.model_copy(update={"stop_order": stop})
        log.info(
            "booked" if auto else "offered",
            extra={
                "field_id": field_id,
                "baler_id": cand.baler.baler_id,
                "date": str(cand.day),
                "attempt": attempt,
            },
        )
        return _to_booked(booking, cand.baler, buyer)
    return NoSlot(field_id=field_id, reason="contention", detail="capacity taken during booking")


def _new_booking(
    field: Field, cand: Candidate, buyer: Buyer | None, q: Quote, *, offered: bool = False, attempt: int = 1
) -> Booking:
    now = clock.now()
    return Booking(
        booking_id=f"BK-{uuid.uuid4().hex[:12]}",
        field_id=field.field_id,
        phone=field.phone,
        village_id=field.village_id,
        baler_id=cand.baler.baler_id,
        buyer_id=buyer.buyer_id if buyer else None,
        date=cand.day,
        acres=field.acres,
        est_tonnes=q.est_tonnes,
        lat=field.lat,
        lng=field.lng,
        buyer_price_per_tonne=buyer.price_per_tonne if buyer else None,
        farmer_payout=q.farmer_payout,
        status=BookingStatus.OFFERED if offered else BookingStatus.CONFIRMED,
        created_at=now,
        attempt=attempt,
        offered_at=now if offered else None,
        expires_at=offer_expiry(cand.day) if offered else None,
    )


def _commit(field: Field, cand: Candidate, buyer: Buyer | None, booking: Booking) -> None:
    cap = cand.baler.acres_per_day
    a = field.acres
    tx = TxBuilder()
    if a > cap:
        capacity_cond = "attribute_not_exists(booked_acres) OR booked_acres = :zero"
        values = {":a": a, ":cap": cap, ":zero": 0, ":one": 1}
    else:
        capacity_cond = "attribute_not_exists(booked_acres) OR booked_acres <= :cap_minus_a"
        values = {":a": a, ":cap": cap, ":zero": 0, ":one": 1, ":cap_minus_a": cap - a}
    tx.update(
        "BalerDays",
        {"baler_id": cand.baler.baler_id, "date": cand.day.isoformat()},
        "SET booked_acres = if_not_exists(booked_acres, :zero) + :a, capacity_acres = :cap, "
        "stop_count = if_not_exists(stop_count, :zero) + :one",
        values=values,
        condition=capacity_cond,
    )
    tx.put("Bookings", to_item(booking), condition="attribute_not_exists(booking_id)")
    tx.update(
        "Fields",
        {"field_id": field.field_id},
        "SET #s = :booked, booking_id = :bid, booking_state = :state, updated_at = :now, "
        "risk_score = :zero, risk_level = :green, risk_reasons = :reasons",
        values={
            ":booked": FieldStatus.BOOKED.value,
            ":bid": booking.booking_id,
            ":state": "offered" if booking.status == BookingStatus.OFFERED else "confirmed",
            ":now": clock.now().isoformat(),
            ":r": FieldStatus.REGISTERED.value,
            ":h": FieldStatus.HARVESTED.value,
            ":zero": 0,
            ":green": "GREEN",
            ":reasons": ["booked"],
        },
        names={"#s": "status"},
        condition="#s IN (:r, :h)",
    )
    if buyer is not None:
        # DynamoDB conditions can't do arithmetic on attributes, so pin demand to the value we read
        # and compare reserved against (demand − tonnes) computed here.
        tx.update(
            "Buyers",
            {"buyer_id": buyer.buyer_id},
            "SET reserved_tonnes = reserved_tonnes + :t",
            values={
                ":t": booking.est_tonnes,
                ":demand": buyer.demand_tonnes,
                ":max_reserved": buyer.demand_tonnes - booking.est_tonnes,
            },
            condition="demand_tonnes = :demand AND reserved_tonnes <= :max_reserved",
        )
    tx.execute()


def recompute_stop_order(baler_id: str, d: date) -> list[Booking]:
    """Re-number the day's confirmed stops by nearest neighbour from the baler's base."""
    baler = BalersRepo().get(baler_id)
    repo = BookingsRepo()
    stops = repo.confirmed_by_baler(baler_id, d)
    if baler is None or not stops:
        return []
    ordered = nearest_neighbour_order((baler.lat, baler.lng), stops)
    result = []
    for i, bk in enumerate(ordered, start=1):
        if bk.stop_order != i:
            repo.set_stop_order(bk.booking_id, i)
        result.append(bk.model_copy(update={"stop_order": i}))
    return result


def _release(bk: Booking, outcome: BookingStatus, today: date, extra: dict[str, str] | None = None) -> bool:
    """End an open booking without a pickup: free the baler-day and the buyer reservation, and put
    the field back to unbooked. One transaction, conditional on the status we read, so a cancel, an
    accept and an expiry racing each other have exactly one winner."""
    field = FieldsRepo().get(bk.field_id)
    if field is None:
        return False
    harvested = field.harvest_confirmed or today >= field.harvest_date
    new_status = FieldStatus.HARVESTED if harvested else FieldStatus.REGISTERED
    now = clock.now().isoformat()
    changes = {"status": outcome.value, "responded_at": now, **(extra or {})}
    if outcome == BookingStatus.CANCELLED:
        del changes["responded_at"]

    tx = TxBuilder()
    tx.update(
        "Bookings",
        {"booking_id": bk.booking_id},
        "SET " + ", ".join(f"#{k} = :{k}" for k in changes),
        values={f":{k}": v for k, v in changes.items()} | {":was": bk.status.value},
        names={f"#{k}": k for k in changes},
        condition="#status = :was",
    )
    tx.update(
        "BalerDays",
        {"baler_id": bk.baler_id, "date": bk.date.isoformat()},
        "SET booked_acres = booked_acres - :a, stop_count = stop_count - :one",
        values={":a": bk.acres, ":one": 1},
        condition="attribute_exists(booked_acres)",
    )
    tx.update(
        "Fields",
        {"field_id": field.field_id},
        "SET #s = :ns, updated_at = :now REMOVE booking_id, booking_state",
        values={":ns": new_status.value, ":now": now, ":bid": bk.booking_id},
        names={"#s": "status"},
        condition="booking_id = :bid",
    )
    if bk.buyer_id:
        tx.update(
            "Buyers",
            {"buyer_id": bk.buyer_id},
            "SET reserved_tonnes = reserved_tonnes - :t",
            values={":t": bk.est_tonnes},
            condition="attribute_exists(buyer_id)",
        )
    try:
        tx.execute()
    except TransactionCancelled as e:
        log.info("release conflict", extra={"booking_id": bk.booking_id, "reasons": e.reasons})
        return False
    if bk.status == BookingStatus.CONFIRMED:
        recompute_stop_order(bk.baler_id, bk.date)
    from clearsky.domain.risk import refresh_field

    refresh_field(bk.field_id, today)
    return True


def cancel_booking(booking_id: str, today: date | None = None) -> bool:
    """Cancel an open booking (an offer or a confirmed pickup) and release capacity and reservation."""
    bk = BookingsRepo().get(booking_id)
    if bk is None or bk.status not in OPEN_BOOKING_STATUSES:
        return False
    return _release(bk, BookingStatus.CANCELLED, today or clock.today())


class OfferResult(BaseModel):
    ok: bool
    error: str | None = None  # not_found | forbidden | not_offered | expired
    booking: Booking | None = None


def _own_offer(booking_id: str, baler_id: str | None) -> OfferResult:
    bk = BookingsRepo().get(booking_id)
    if bk is None:
        return OfferResult(ok=False, error="not_found")
    if baler_id is not None and bk.baler_id != baler_id:
        return OfferResult(ok=False, error="forbidden")
    if bk.status != BookingStatus.OFFERED:
        return OfferResult(ok=False, error="not_offered", booking=bk)
    return OfferResult(ok=True, booking=bk)


def accept_offer(booking_id: str, baler_id: str | None = None) -> OfferResult:
    """The baler says yes: OFFERED → CONFIRMED, if the offer has not expired. The stop joins the route."""
    found = _own_offer(booking_id, baler_id)
    if not found.ok or found.booking is None:
        return found
    bk = found.booking
    now = clock.now()
    if bk.expires_at is not None and _aware(bk.expires_at) <= now:
        return OfferResult(ok=False, error="expired", booking=bk)
    tx = TxBuilder()
    tx.update(
        "Bookings",
        {"booking_id": booking_id},
        "SET #s = :confirmed, responded_at = :now",
        values={
            ":confirmed": BookingStatus.CONFIRMED.value,
            ":offered": BookingStatus.OFFERED.value,
            ":now": now.isoformat(),
        },
        names={"#s": "status"},
        condition="#s = :offered AND (attribute_not_exists(expires_at) OR expires_at > :now)",
    )
    tx.update(
        "Fields",
        {"field_id": bk.field_id},
        "SET booking_state = :state, updated_at = :now",
        values={":state": "confirmed", ":now": now.isoformat(), ":bid": booking_id},
        condition="booking_id = :bid",
    )
    try:
        tx.execute()
    except TransactionCancelled:
        fresh = BookingsRepo().get(booking_id)
        still_offered = fresh is not None and fresh.status == BookingStatus.OFFERED
        return OfferResult(ok=False, error="expired" if still_offered else "not_offered", booking=fresh)
    ordered = recompute_stop_order(bk.baler_id, bk.date)
    stop = next((b.stop_order for b in ordered if b.booking_id == booking_id), 0)
    confirmed = bk.model_copy(
        update={"status": BookingStatus.CONFIRMED, "stop_order": stop, "responded_at": now}
    )
    return OfferResult(ok=True, booking=confirmed)


def release_offer(
    booking_id: str,
    outcome: BookingStatus,
    baler_id: str | None = None,
    reason: str | None = None,
    note: str | None = None,
    today: date | None = None,
) -> OfferResult:
    """An offer ends without a pickup: the baler declined (`DECLINED`) or did not answer (`EXPIRED`)."""
    found = _own_offer(booking_id, baler_id)
    if not found.ok or found.booking is None:
        return found
    bk = found.booking
    extra = {k: v for k, v in (("decline_reason", reason), ("decline_note", note)) if v}
    if not _release(bk, outcome, today or clock.today(), extra):
        return OfferResult(ok=False, error="not_offered", booking=BookingsRepo().get(booking_id))
    return OfferResult(ok=True, booking=bk.model_copy(update={"status": outcome, **extra}))


class DoneResult(BaseModel):
    ok: bool
    error: str | None = None  # not_found | forbidden | not_confirmed
    booking: Booking | None = None


def mark_done(booking_id: str, baler_id: str | None = None) -> DoneResult:
    """Operator finished a field: booking DONE, field CLEARED, buyer received += tonnes (one transaction).

    `baler_id` (from the operator's JWT) must own the booking; None means an officer is acting.
    """
    bk = BookingsRepo().get(booking_id)
    if bk is None:
        return DoneResult(ok=False, error="not_found")
    if baler_id is not None and bk.baler_id != baler_id:
        return DoneResult(ok=False, error="forbidden")
    if bk.status != BookingStatus.CONFIRMED:
        return DoneResult(ok=False, error="not_confirmed", booking=bk)
    # Deliver to the best buyer at pickup time: one that joined or raised its price since booking wins.
    if rematch_booking(booking_id):
        bk = BookingsRepo().get(booking_id) or bk
    now = clock.now().isoformat()
    # Straw that was baled was not burnt: freeze the estimate with today's factors (empty if none are set).
    snap = impact.snapshot(bk.est_tonnes)
    tx = TxBuilder()
    tx.update(
        "Bookings",
        {"booking_id": booking_id},
        "SET #s = :done, done_at = :now" + "".join(f", {k} = :{k}" for k in snap),
        values={":done": BookingStatus.DONE.value, ":confirmed": BookingStatus.CONFIRMED.value, ":now": now}
        | {f":{k}": v for k, v in snap.items()},
        names={"#s": "status"},
        condition="#s = :confirmed",
    )
    tx.update(
        "Fields",
        {"field_id": bk.field_id},
        "SET #s = :cleared, updated_at = :now, risk_score = :zero, risk_level = :green, "
        "risk_reasons = :reasons REMOVE booking_state",
        values={
            ":cleared": FieldStatus.CLEARED.value,
            ":now": now,
            ":zero": 0,
            ":green": "GREEN",
            ":reasons": ["cleared"],
            ":bid": booking_id,
        },
        names={"#s": "status"},
        condition="booking_id = :bid",
    )
    if bk.buyer_id:
        tx.update(
            "Buyers",
            {"buyer_id": bk.buyer_id},
            "SET received_tonnes = if_not_exists(received_tonnes, :zero) + :t",
            values={":t": bk.est_tonnes, ":zero": 0},
            condition="attribute_exists(buyer_id)",
        )
    try:
        tx.execute()
    except TransactionCancelled:
        return DoneResult(ok=False, error="not_confirmed", booking=BookingsRepo().get(booking_id))
    from clearsky.domain.risk import refresh_village

    refresh_village(bk.village_id)
    return DoneResult(ok=True, booking=bk.model_copy(update={"status": BookingStatus.DONE, **snap}))


# ----------------------------------------------------------------- buyer re-matching


def net_price(buyer: Buyer, lat: float, lng: float) -> tuple[float, float]:
    """(₹ per tonne after transport, distance km) for straw picked up at (lat, lng)."""
    dist = haversine_km(lat, lng, buyer.lat, buyer.lng)
    return buyer.price_per_tonne - get_settings().transport_cost_per_tonne_km * dist, dist


def better_buyer(bk: Booking, buyers: list[Buyer]) -> Buyer | None:
    """A buyer that pays strictly more after transport than the booking's current buyer, within its
    own radius and with room for this straw; None if the current buyer is still the best."""
    current = next((b for b in buyers if b.buyer_id == bk.buyer_id), None)
    best_net = net_price(current, bk.lat, bk.lng)[0] if current else float("-inf")
    best: Buyer | None = None
    for b in buyers:
        if b.buyer_id == bk.buyer_id or b.remaining_tonnes < bk.est_tonnes:
            continue
        net, dist = net_price(b, bk.lat, bk.lng)
        if dist > b.max_radius_km:
            continue
        if net > best_net + 0.005 or (best is not None and net == best_net and b.buyer_id < best.buyer_id):
            best, best_net = b, net
    return best


def _move_buyer(bk: Booking, new: Buyer) -> bool:
    """Point an open booking at `new` and move its reservation, in one transaction.

    Conditional on the booking's status and buyer as read and on `new` still having room, so a
    concurrent accept, cancel, Done or demand change makes this a no-op instead of a double count.
    The farmer's payout is what they were promised and does not change.
    """
    now = clock.now()
    sets = "buyer_id = :new, buyer_price_per_tonne = :price, buyer_changed_at = :now"
    values: dict[str, object] = {
        ":new": new.buyer_id,
        ":price": new.price_per_tonne,
        ":now": now.isoformat(),
        ":was": bk.status.value,
    }
    if bk.buyer_id:
        sets += ", previous_buyer_id = :old"
        values[":old"] = bk.buyer_id
    tx = TxBuilder()
    tx.update(
        "Bookings",
        {"booking_id": bk.booking_id},
        "SET " + sets,
        values=values,
        names={"#s": "status"},
        condition="#s = :was AND " + ("buyer_id = :old" if bk.buyer_id else "attribute_not_exists(buyer_id)"),
    )
    if bk.buyer_id:
        tx.update(
            "Buyers",
            {"buyer_id": bk.buyer_id},
            "SET reserved_tonnes = reserved_tonnes - :t",
            values={":t": bk.est_tonnes},
            condition="attribute_exists(buyer_id)",
        )
    tx.update(
        "Buyers",
        {"buyer_id": new.buyer_id},
        "SET reserved_tonnes = reserved_tonnes + :t",
        values={
            ":t": bk.est_tonnes,
            ":demand": new.demand_tonnes,
            ":max_reserved": new.demand_tonnes - bk.est_tonnes,
        },
        condition="demand_tonnes = :demand AND reserved_tonnes <= :max_reserved",
    )
    try:
        tx.execute()
    except TransactionCancelled as e:
        log.info("buyer re-match skipped", extra={"booking_id": bk.booking_id, "reasons": e.reasons})
        return False
    log.info(
        "buyer re-matched",
        extra={"booking_id": bk.booking_id, "from": bk.buyer_id, "to": new.buyer_id, "tonnes": bk.est_tonnes},
    )
    return True


def rematch_booking(booking_id: str) -> bool:
    """Send one open booking's straw to a better-paying buyer if there is one now."""
    bk = BookingsRepo().get(booking_id)
    if bk is None or bk.status not in OPEN_BOOKING_STATUSES:
        return False
    new = better_buyer(bk, BuyersRepo().list_all())
    return _move_buyer(bk, new) if new else False


def rematch_open_bookings() -> int:
    """Re-check every open booking against today's buyers (run when a buyer joins or changes their
    demand, price or radius). Oldest booking first; buyers are re-read after every move because
    reservations change. Delivered (DONE) straw is never moved. Returns how many bookings moved."""
    open_bookings = sorted(
        (b for b in BookingsRepo().list_all() if b.status in OPEN_BOOKING_STATUSES),
        key=lambda b: (b.created_at, b.booking_id),
    )
    buyers = BuyersRepo().list_all()
    moved = 0
    for bk in open_bookings:
        new = better_buyer(bk, buyers)
        if new and _move_buyer(bk, new):
            moved += 1
            buyers = BuyersRepo().list_all()
    if moved:
        log.info("buyers re-matched", extra={"moved": moved, "checked": len(open_bookings)})
    return moved


def reschedule(field_id: str, new_harvest_date: date, today: date | None = None) -> BookingResult:
    """Move a field's harvest date: cancel any booking, update dates, book again."""
    today = today or clock.today()
    fields = FieldsRepo()
    field = fields.get(field_id)
    if field is None:
        return NoSlot(field_id=field_id, reason="not_found")
    if field.status in (FieldStatus.CLEARED, FieldStatus.FIRE_REPORTED):
        return NoSlot(field_id=field_id, reason="not_bookable", detail=f"status {field.status.value}")
    if field.booking_id:
        cancel_booking(field.booking_id, today)
        field = fields.get(field_id) or field
    status = FieldStatus.HARVESTED if today >= new_harvest_date else FieldStatus.REGISTERED
    fields.update(
        field_id,
        {
            "harvest_date": new_harvest_date,
            "sowing_deadline": compute_sowing_deadline(new_harvest_date),
            "harvest_confirmed": False,
            "status": status,
            "updated_at": clock.now().isoformat(),
        },
    )
    return book_pickup(field_id, today)


def new_field_id() -> str:
    return f"F-{uuid.uuid4().hex[:12]}"
