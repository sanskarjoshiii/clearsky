"""Agent tool implementations (IMPLEMENTATION.md §7.2).

Every function takes the verified sender `phone` as its first argument. The LLM never supplies a
phone number: `agent.build_agent` binds it by closure. Validation lives here, not in the prompt.
Each tool returns a JSON-serialisable dict; failures are `{"ok": False, "error": <code>, "message": ...}`
so the model can explain the problem to the farmer.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from clearsky import clock
from clearsky.config import get_settings
from clearsky.domain import matching, risk
from clearsky.domain.geo import jitter_point
from clearsky.domain.villages import resolve
from clearsky.models import BookingStatus, Farmer, Field, FieldStatus, Language
from clearsky.models.enums import OPEN_BOOKING_STATUSES, REFUSED_BOOKING_STATUSES
from clearsky.repo import BookingsRepo, FarmersRepo, FieldsRepo, VillagesRepo

MIN_ACRES, MAX_ACRES = 0.5, 100.0
FIELD_JITTER_KM = 1.5

Result = dict[str, Any]


def _err(code: str, message: str) -> Result:
    return {"ok": False, "error": code, "message": message}


def _parse_date(value: str, label: str) -> date | Result:
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return _err("bad_date", f"{label} must be YYYY-MM-DD, got {value!r}")


def _owned_field(phone: str, field_id: str) -> Field | Result:
    field = FieldsRepo().get(field_id)
    if field is None or field.phone != phone:
        return _err("field_not_found", "No such field for this farmer.")
    return field


def _field_view(f: Field) -> Result:
    return {
        "field_id": f.field_id,
        "village_id": f.village_id,
        "acres": f.acres,
        "harvest_date": f.harvest_date.isoformat(),
        "sowing_deadline": f.sowing_deadline.isoformat(),
        "harvest_confirmed": f.harvest_confirmed,
        "status": f.status.value,
        "booking_id": f.booking_id,
    }


def _booking_view(result: matching.BookingResult) -> Result:
    if isinstance(result, matching.NoSlot):
        return {
            "ok": False,
            "error": "no_slot",
            "reason": result.reason,
            "field_id": result.field_id,
            "message": _NO_SLOT_MESSAGES.get(result.reason, result.reason),
        }
    offered = result.status == "offered"
    return {
        "ok": True,
        # "offered": the request is with the baler and NOT confirmed yet. The farmer gets a separate
        # WhatsApp message when the baler accepts; never say the pickup is confirmed before that.
        "status": result.status,
        "confirmed": not offered,
        "next_step": "Baler must accept. Tell the farmer you will confirm soon." if offered else "Confirmed.",
        "booking_id": result.booking_id,
        "field_id": result.field_id,
        "pickup_date": result.date.isoformat(),
        "stop_order": result.stop_order,
        "operator_name": result.operator_name,
        "chc_name": result.chc_name,
        "straw_goes_to": result.buyer_name or "village storage (buyer pending)",
        "est_tonnes": result.est_tonnes,
        "farmer_payout_inr": result.farmer_payout,
        "free_clearance": result.free_clearance,
        "payout_is_estimate": True,
        "already_booked": result.already_booked,
    }


_NO_SLOT_MESSAGES = {
    "not_found": "Field not found.",
    "not_bookable": "This field can't be booked in its current state.",
    "deadline_too_close": "The sowing deadline is too close to schedule a baler.",
    "no_baler_capacity": "No baler is free before the sowing deadline. An officer will follow up.",
    "contention": "Balers filled up while booking. Please try again.",
    "no_baler_accepted": "No baler has accepted yet. An officer will follow up.",
}


# ------------------------------------------------------------------- tools


def get_my_profile(phone: str) -> Result:
    farmer = FarmersRepo().get(phone)
    if farmer is None:
        return {"ok": True, "registered": False}
    fields = FieldsRepo().by_farmer(phone)
    village = VillagesRepo().get(farmer.village_id)
    return {
        "ok": True,
        "registered": True,
        "name": farmer.name,
        "village_id": farmer.village_id,
        "village_name": village.name if village else None,
        "language": farmer.language.value,
        "fields": [_field_view(f) for f in fields],
        "bookings": get_my_bookings(phone)["bookings"],
    }


def resolve_village(name: str) -> Result:
    if not name or not name.strip():
        return _err("empty_name", "Village name is empty.")
    matches = resolve(name)
    if not matches:
        return {"ok": True, "matches": [], "message": "No village matched. Ask the farmer for a nearby town."}
    return {"ok": True, "matches": [m.model_dump() for m in matches]}


def register_farmer(phone: str, name: str, village_id: str, language: str = "hi") -> Result:
    name = (name or "").strip()
    if not 1 <= len(name) <= 60:
        return _err("bad_name", "Name must be 1–60 characters.")
    if VillagesRepo().get(village_id) is None:
        return _err("unknown_village", "Unknown village_id. Use resolve_village first.")
    try:
        lang = Language(language)
    except ValueError:
        lang = Language.HINDI
    repo = FarmersRepo()
    existing = repo.get(phone)
    farmer = Farmer(
        phone=phone,
        name=name,
        village_id=village_id,
        language=lang,
        created_at=existing.created_at if existing else clock.now(),
    )
    repo.put(farmer)
    return {"ok": True, "name": farmer.name, "village_id": village_id, "updated": existing is not None}


def register_field(
    phone: str, acres: float, harvest_date: str, village_id: str, sowing_date: str | None = None
) -> Result:
    s = get_settings()
    today = clock.today()
    if FarmersRepo().get(phone) is None:
        return _err("farmer_not_registered", "Register the farmer (name, village) first.")
    try:
        acres = float(acres)
    except (TypeError, ValueError):
        return _err("bad_acres", "Acres must be a number.")
    if not MIN_ACRES <= acres <= MAX_ACRES:
        return _err("bad_acres", f"Acres must be between {MIN_ACRES} and {MAX_ACRES}.")
    hd = _parse_date(harvest_date, "harvest_date")
    if isinstance(hd, dict):
        return hd
    earliest = max(s.season_start, today - timedelta(days=s.harvest_lookback_days))
    latest = s.season_sowing_cutoff - timedelta(days=s.sowing_buffer_days + 1)
    if hd < earliest:
        return _err("harvest_date_too_old", f"Harvest date must be on or after {earliest.isoformat()}.")
    if hd > latest:
        return _err("harvest_date_out_of_season", f"Harvest date must be on or before {latest.isoformat()}.")
    sd: date | None = None
    if sowing_date:
        parsed = _parse_date(sowing_date, "sowing_date")
        if isinstance(parsed, dict):
            return parsed
        if parsed <= hd:
            return _err("bad_sowing_date", "Sowing date must be after the harvest date.")
        sd = parsed
    village = VillagesRepo().get(village_id)
    if village is None:
        return _err("unknown_village", "Unknown village_id. Use resolve_village first.")

    fields = FieldsRepo()
    for f in fields.by_farmer(phone):  # idempotent: the model may retry the same call
        if (
            f.village_id == village_id
            and f.harvest_date == hd
            and f.acres == acres
            and f.status not in (FieldStatus.CLEARED, FieldStatus.FIRE_REPORTED)
        ):
            return {"ok": True, "duplicate": True, **_field_view(f)}

    lat, lng = jitter_point(village.lat, village.lng, FIELD_JITTER_KM, random.Random())
    now = clock.now()
    field = Field(
        field_id=matching.new_field_id(),
        phone=phone,
        village_id=village_id,
        acres=acres,
        lat=lat,
        lng=lng,
        harvest_date=hd,
        sowing_deadline=matching.compute_sowing_deadline(hd, sd),
        status=FieldStatus.HARVESTED if hd <= today else FieldStatus.REGISTERED,
        harvest_confirmed=hd < today,
        source="whatsapp",
        created_at=now,
        updated_at=now,
    )
    fields.put(field)
    return {"ok": True, **_field_view(field)}


def book_pickup(phone: str, field_id: str) -> Result:
    owned = _owned_field(phone, field_id)
    if isinstance(owned, dict):
        return owned
    result = matching.book_pickup(field_id)
    if isinstance(result, matching.NoSlot):
        risk.refresh_field(field_id)  # the radar should show "no baler free" right away
    return _booking_view(result)


def get_my_bookings(phone: str) -> Result:
    repo = BookingsRepo()
    out = []
    for f in FieldsRepo().by_farmer(phone):
        for bk in repo.by_field(f.field_id):
            if bk.status == BookingStatus.CANCELLED or bk.status in REFUSED_BOOKING_STATUSES:
                continue
            out.append(
                {
                    "booking_id": bk.booking_id,
                    "field_id": bk.field_id,
                    "pickup_date": bk.date.isoformat(),
                    "status": bk.status.value,  # OFFERED = waiting for the baler, not confirmed yet
                    "confirmed": bk.status != BookingStatus.OFFERED,
                    "acres": bk.acres,
                    "farmer_payout_inr": bk.farmer_payout,
                    "free_clearance": bk.farmer_payout <= 0,
                }
            )
    out.sort(key=lambda b: str(b["pickup_date"]))
    return {"ok": True, "bookings": out}


def confirm_harvest(phone: str, field_id: str) -> Result:
    owned = _owned_field(phone, field_id)
    if isinstance(owned, dict):
        return owned
    values: dict[str, Any] = {"harvest_confirmed": True, "updated_at": clock.now().isoformat()}
    if owned.status == FieldStatus.REGISTERED:
        values["status"] = FieldStatus.HARVESTED
    FieldsRepo().update(field_id, values)
    risk.refresh_field(field_id)
    updated = FieldsRepo().get(field_id) or owned
    return {"ok": True, **_field_view(updated)}


def reschedule(phone: str, field_id: str, new_harvest_date: str) -> Result:
    owned = _owned_field(phone, field_id)
    if isinstance(owned, dict):
        return owned
    hd = _parse_date(new_harvest_date, "new_harvest_date")
    if isinstance(hd, dict):
        return hd
    s = get_settings()
    today = clock.today()
    earliest = max(s.season_start, today - timedelta(days=s.harvest_lookback_days))
    latest = s.season_sowing_cutoff - timedelta(days=s.sowing_buffer_days + 1)
    if not earliest <= hd <= latest:
        return _err("harvest_date_out_of_range", f"New harvest date must be {earliest}..{latest}.")
    return _booking_view(matching.reschedule(field_id, hd))


def cancel_booking(phone: str, booking_id: str) -> Result:
    bk = BookingsRepo().get(booking_id)
    if bk is None or bk.phone != phone:
        return _err("booking_not_found", "No such booking for this farmer.")
    if bk.status not in OPEN_BOOKING_STATUSES:
        return _err("not_cancellable", f"Booking is {bk.status.value}.")
    ok = matching.cancel_booking(booking_id)
    return {"ok": ok} if ok else _err("cancel_failed", "Could not cancel right now. Try again.")
